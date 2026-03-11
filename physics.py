import pygame

from constants import (
    BALL_COLLISION_DAMP,
    BALL_DIAMETER_MM,
    BALL_RADIUS_MM,
    BLACK_START_POS,
    FRICTION,
    MAX_FOULS,
    MIN_SPEED,
    PHASE_AIM,
    PHASE_MOVING,
    PHASE_ROUND_OVER,
    TABLE_HEIGHT_MM,
    TABLE_WIDTH_MM,
    WALL_BOUNCE,
)
from geometry import (
    is_ball_in_pocket_corridor,
    is_in_bottom_corner_opening,
    is_in_left_corner_opening,
    is_in_right_corner_opening,
    is_in_top_corner_opening,
)
from models import Ball, GameState, cue_ball, is_any_ball_moving, target_balls_remaining
import math


def handle_wall_bounce(ball: Ball) -> None:
    if ball.pos.x - BALL_RADIUS_MM < 0:
        if is_in_left_corner_opening(ball):
            ball.pos.x = min(ball.pos.x, 0)
        else:
            ball.pos.x = BALL_RADIUS_MM
            ball.vel.x = abs(ball.vel.x) * WALL_BOUNCE
    elif ball.pos.x + BALL_RADIUS_MM > TABLE_WIDTH_MM:
        if is_in_right_corner_opening(ball):
            ball.pos.x = max(ball.pos.x, TABLE_WIDTH_MM)
        else:
            ball.pos.x = TABLE_WIDTH_MM - BALL_RADIUS_MM
            ball.vel.x = -abs(ball.vel.x) * WALL_BOUNCE

    if ball.pos.y - BALL_RADIUS_MM < 0:
        if is_in_top_corner_opening(ball):
            ball.pos.y = min(ball.pos.y, 0)
        else:
            ball.pos.y = BALL_RADIUS_MM
            ball.vel.y = abs(ball.vel.y) * WALL_BOUNCE
    elif ball.pos.y + BALL_RADIUS_MM > TABLE_HEIGHT_MM:
        if is_in_bottom_corner_opening(ball):
            ball.pos.y = max(ball.pos.y, TABLE_HEIGHT_MM)
        else:
            ball.pos.y = TABLE_HEIGHT_MM - BALL_RADIUS_MM
            ball.vel.y = -abs(ball.vel.y) * WALL_BOUNCE


def is_position_free(state: GameState, pos: pygame.Vector2) -> bool:
    margin = BALL_RADIUS_MM + 4.0
    if not (margin <= pos.x <= TABLE_WIDTH_MM - margin and margin <= pos.y <= TABLE_HEIGHT_MM - margin):
        return False

    probe = Ball(name="_probe", pos=pos, vel=pygame.Vector2(), color=(0, 0, 0), is_cue=False, active=True)
    if is_ball_in_pocket_corridor(probe):
        return False

    min_dist_sq = BALL_DIAMETER_MM * BALL_DIAMETER_MM
    for ball in state.balls:
        if not ball.active:
            continue
        if (ball.pos - pos).length_squared() < min_dist_sq:
            return False
    return True


def find_safe_spot(state: GameState, preferred: pygame.Vector2) -> pygame.Vector2:
    step = BALL_DIAMETER_MM + 8.0
    offsets = [pygame.Vector2()]

    for ring in range(1, 7):
        for dx in range(-ring, ring + 1):
            for dy in range(-ring, ring + 1):
                if max(abs(dx), abs(dy)) != ring:
                    continue
                offsets.append(pygame.Vector2(dx * step, dy * step))

    for offset in offsets:
        candidate = preferred + offset
        if is_position_free(state, candidate):
            return candidate

    return preferred


def place_ball_safely(state: GameState, ball: Ball, preferred: pygame.Vector2) -> None:
    ball.active = True
    ball.vel.update(0, 0)
    ball.pos = find_safe_spot(state, preferred)


def place_cue_ball(state: GameState) -> None:
    cue = cue_ball(state)
    place_ball_safely(state, cue, BLACK_START_POS)


def update_ball(ball: Ball, dt: float) -> None:
    speed = ball.vel.length()
    if speed <= 0:
        return

    ball.pos += ball.vel * dt
    handle_wall_bounce(ball)

    new_speed = max(0.0, speed - FRICTION * dt)
    if new_speed < MIN_SPEED:
        ball.vel.update(0, 0)
    else:
        ball.vel.scale_to_length(new_speed)


def resolve_ball_collisions(state: GameState) -> None:
    balls = state.balls
    min_dist = BALL_DIAMETER_MM

    for index, ball_a in enumerate(balls):
        if not ball_a.active:
            continue

        for ball_b in balls[index + 1 :]:
            if not ball_b.active:
                continue

            delta = ball_b.pos - ball_a.pos
            dist_sq = delta.length_squared()
            if dist_sq == 0:
                delta = pygame.Vector2(1, 0)
                dist_sq = 1.0
            if dist_sq > min_dist * min_dist:
                continue

            dist = dist_sq ** 0.5
            normal = delta / dist
            overlap = min_dist - dist

            correction = normal * (overlap * 0.5)
            ball_a.pos -= correction
            ball_b.pos += correction

            if ball_a.is_cue or ball_b.is_cue:
                state.shot_had_contact = True

            v1n = ball_a.vel.dot(normal)
            v2n = ball_b.vel.dot(normal)
            rel = v1n - v2n
            if rel <= 0:
                continue

            ball_a.vel += (v2n - v1n) * normal
            ball_b.vel += (v1n - v2n) * normal
            ball_a.vel *= BALL_COLLISION_DAMP
            ball_b.vel *= BALL_COLLISION_DAMP


def check_pockets(state: GameState) -> None:
    for ball in state.balls:
        if not ball.active:
            continue

        if not is_ball_in_pocket_corridor(ball):
            continue

        if ball.is_cue:
            state.fouls += 1
            state.shot_foul = True
            place_cue_ball(state)
        else:
            state.balls_pocketed += 1
            state.scores[state.current_player] += 1
            state.pocketed_by_player[state.current_player].append(ball)
            state.shot_pocketed += 1
            ball.active = False
            ball.vel.update(0, 0)


def respot_from_penalty(state: GameState) -> None:
    player = state.current_player
    if not state.pocketed_by_player[player]:
        return

    ball = state.pocketed_by_player[player].pop()
    state.scores[player] = max(0, state.scores[player] - 1)
    place_ball_safely(state, ball, BLACK_START_POS)
    state.info_message = f"Фол игрока {player + 1}: шар {ball.name} возвращён на стол"


def settle_round_if_needed(state: GameState) -> None:
    if is_any_ball_moving(state, MIN_SPEED * MIN_SPEED):
        return

    for ball in state.balls:
        if ball.active:
            ball.vel.update(0, 0)

    shot_no_contact = not state.shot_had_contact
    foul_this_shot = state.shot_foul or shot_no_contact

    if foul_this_shot:
        if shot_no_contact and not state.shot_foul:
            state.info_message = "Фол: биток не коснулся шаров"
        state.fouls += int(not state.shot_foul)  # only add if not already counted
        respot_from_penalty(state)

    if target_balls_remaining(state) == 0:
        winner = 1 if state.scores[1] > state.scores[0] else 0
        if state.scores[0] == state.scores[1]:
            state.round_title = "Ничья"
            state.round_message = f"Счёт {state.scores[0]}:{state.scores[1]}. Нажмите R, чтобы начать заново."
        else:
            state.round_title = f"Победа игрока {winner + 1}"
            state.round_message = (
                f"Финальный счёт {state.scores[0]}:{state.scores[1]} за {state.shot_count} ударов. Нажмите R для рестарта."
            )
        state.phase = PHASE_ROUND_OVER
        state.charging = False
    elif state.fouls >= MAX_FOULS:
        state.phase = PHASE_ROUND_OVER
        state.round_title = "Раунд проигран"
        state.round_message = f"Слишком много фолов ({state.fouls}/{MAX_FOULS}). Нажмите R для рестарта."
        state.charging = False
    else:
        change_turn = foul_this_shot or state.shot_pocketed == 0
        if change_turn:
            state.current_player = 1 - state.current_player
            state.info_message = f"Ход игрока {state.current_player + 1}"
        else:
            state.info_message = f"Игрок {state.current_player + 1} продолжает"
        state.phase = PHASE_AIM
        state.charging = False

    state.shot_had_contact = False
    state.shot_pocketed = 0
    state.shot_foul = False


def update_physics(state: GameState, dt: float) -> None:
    if state.phase != PHASE_MOVING:
        return

    for ball in state.balls:
        if ball.active:
            update_ball(ball, dt)

    resolve_ball_collisions(state)
    check_pockets(state)
    settle_round_if_needed(state)


def _simulate_center_bort(v0: float, target_bounces: int, dt: float = 0.002) -> bool:
    """
    Simulate a straight shot from table center to a short rail and back.
    Returns True if the ball hits the center after exactly target_bounces bounces.
    """
    pos = TABLE_HEIGHT_MM * 0.5
    vel = -v0  # towards top rail
    bounces = 0
    center = TABLE_HEIGHT_MM * 0.5

    for _ in range(int(12 / dt)):  # simulate up to 12 seconds
        # advance
        pos += vel * dt

        # rail collision
        if pos <= 0:
            pos = -pos
            vel = abs(vel) * WALL_BOUNCE
            bounces += 1
        elif pos >= TABLE_HEIGHT_MM:
            pos = TABLE_HEIGHT_MM - (pos - TABLE_HEIGHT_MM)
            vel = -abs(vel) * WALL_BOUNCE
            bounces += 1

        speed = abs(vel)
        speed = max(0.0, speed - FRICTION * dt)
        if speed < MIN_SPEED:
            break
        vel = math.copysign(speed, vel)

        # check crossing center after required bounces
        if bounces == target_bounces:
            # detect sign change around center crossing
            if (pos - center) == 0 or ((pos - center) * (pos - center - vel * dt) < 0):
                return True
    return False


def _solve_bort_speed(target_bounces: int) -> float:
    low = 50.0
    high = MAX_SHOT_SPEED
    for _ in range(22):
        mid = (low + high) * 0.5
        if _simulate_center_bort(mid, target_bounces):
            high = mid
        else:
            low = mid
    return high


def compute_bort_speeds(max_borts: int = 4) -> list[float]:
    speeds = []
    for b in range(1, max_borts + 1):
        try:
            speeds.append(_solve_bort_speed(b))
        except Exception:
            break
    return speeds
