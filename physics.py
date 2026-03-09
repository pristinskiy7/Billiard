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


def place_cue_ball(state: GameState) -> None:
    cue = cue_ball(state)
    cue.active = True
    cue.pos = BLACK_START_POS.copy()
    cue.vel.update(0, 0)

    min_dist = BALL_DIAMETER_MM
    for ball in state.balls:
        if ball is cue or not ball.active:
            continue

        delta = ball.pos - cue.pos
        if delta.length_squared() == 0:
            delta = pygame.Vector2(1, 0)
        if delta.length_squared() < min_dist * min_dist:
            ball.pos = cue.pos + delta.normalize() * (min_dist + 1)


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


def resolve_ball_collisions(balls: list[Ball]) -> None:
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
            place_cue_ball(state)
        else:
            state.balls_pocketed += 1
            ball.active = False
            ball.vel.update(0, 0)


def settle_round_if_needed(state: GameState) -> None:
    if is_any_ball_moving(state, MIN_SPEED * MIN_SPEED):
        return

    for ball in state.balls:
        if ball.active:
            ball.vel.update(0, 0)

    if state.fouls >= MAX_FOULS:
        state.phase = PHASE_ROUND_OVER
        state.round_title = "Round Lost"
        state.round_message = f"Too many fouls ({state.fouls}/{MAX_FOULS}). Press R to restart."
        state.charging = False
        return

    if target_balls_remaining(state) == 0:
        state.phase = PHASE_ROUND_OVER
        state.round_title = "Round Won"
        state.round_message = f"All targets cleared in {state.shot_count} shots. Press R to restart."
        state.charging = False
        return

    state.phase = PHASE_AIM
    state.charging = False


def update_physics(state: GameState, dt: float) -> None:
    if state.phase != PHASE_MOVING:
        return

    for ball in state.balls:
        if ball.active:
            update_ball(ball, dt)

    resolve_ball_collisions(state.balls)
    check_pockets(state)
    settle_round_if_needed(state)
