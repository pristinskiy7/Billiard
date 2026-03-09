import os
import sys
from dataclasses import dataclass, field

import pygame


WIDTH = 1000
HEIGHT = 600
FPS = 120

TABLE_MARGIN = 60
TABLE_RECT = pygame.Rect(
    TABLE_MARGIN,
    TABLE_MARGIN,
    WIDTH - TABLE_MARGIN * 2,
    HEIGHT - TABLE_MARGIN * 2,
)

BALL_RADIUS = 15
POCKET_RADIUS = 28

FRICTION = 230.0
MIN_SPEED = 8.0
WALL_BOUNCE = 0.92
BALL_COLLISION_DAMP = 0.98
SHOT_POWER_SCALE = 6.0
MAX_SHOT_SPEED = 1100.0
MIN_SHOT_SPEED = 25.0

PHASE_AIM = "aim"
PHASE_MOVING = "moving"
PHASE_ROUND_OVER = "round_over"

BG_COLOR = (76, 52, 35)
TABLE_COLOR = (20, 120, 20)
RAIL_COLOR = (36, 86, 36)
BALL_COLOR = (245, 245, 245)
TARGET_BALL_COLOR = (220, 70, 70)
POCKET_COLOR = (18, 18, 18)
AIM_COLOR = (255, 232, 128)
BAR_BG = (30, 30, 30)
BAR_FILL = (255, 200, 40)
TEXT_COLOR = (245, 245, 245)
OVERLAY_COLOR = (0, 0, 0, 150)

POCKETS = [
    pygame.Vector2(TABLE_RECT.left, TABLE_RECT.top),
    pygame.Vector2(TABLE_RECT.centerx, TABLE_RECT.top),
    pygame.Vector2(TABLE_RECT.right, TABLE_RECT.top),
    pygame.Vector2(TABLE_RECT.left, TABLE_RECT.bottom),
    pygame.Vector2(TABLE_RECT.centerx, TABLE_RECT.bottom),
    pygame.Vector2(TABLE_RECT.right, TABLE_RECT.bottom),
]

CUE_START_POS = pygame.Vector2(TABLE_RECT.left + 180, TABLE_RECT.centery)
TARGET_START_POS = pygame.Vector2(TABLE_RECT.right - 220, TABLE_RECT.centery)


@dataclass
class Ball:
    name: str
    pos: pygame.Vector2
    vel: pygame.Vector2
    color: tuple[int, int, int]
    is_cue: bool
    active: bool = True


@dataclass
class GameState:
    balls: list[Ball] = field(default_factory=list)
    shot_count: int = 0
    balls_pocketed: int = 0
    fouls: int = 0
    phase: str = PHASE_AIM
    charging: bool = False
    round_message: str = ""


def create_balls() -> list[Ball]:
    return [
        Ball(
            name="cue",
            pos=CUE_START_POS.copy(),
            vel=pygame.Vector2(),
            color=BALL_COLOR,
            is_cue=True,
        ),
        Ball(
            name="target_1",
            pos=TARGET_START_POS.copy(),
            vel=pygame.Vector2(),
            color=TARGET_BALL_COLOR,
            is_cue=False,
        ),
    ]


def create_initial_state() -> GameState:
    return GameState(balls=create_balls())


def reset_round(state: GameState) -> None:
    state.balls = create_balls()
    state.shot_count = 0
    state.balls_pocketed = 0
    state.fouls = 0
    state.phase = PHASE_AIM
    state.charging = False
    state.round_message = ""


def cue_ball(state: GameState) -> Ball:
    return state.balls[0]


def target_balls_remaining(state: GameState) -> int:
    return sum(1 for ball in state.balls if not ball.is_cue and ball.active)


def is_any_ball_moving(state: GameState) -> bool:
    threshold = MIN_SPEED * MIN_SPEED
    return any(ball.active and ball.vel.length_squared() > threshold for ball in state.balls)


def handle_wall_bounce(ball: Ball) -> None:
    if ball.pos.x - BALL_RADIUS < TABLE_RECT.left:
        ball.pos.x = TABLE_RECT.left + BALL_RADIUS
        ball.vel.x = abs(ball.vel.x) * WALL_BOUNCE
    elif ball.pos.x + BALL_RADIUS > TABLE_RECT.right:
        ball.pos.x = TABLE_RECT.right - BALL_RADIUS
        ball.vel.x = -abs(ball.vel.x) * WALL_BOUNCE

    if ball.pos.y - BALL_RADIUS < TABLE_RECT.top:
        ball.pos.y = TABLE_RECT.top + BALL_RADIUS
        ball.vel.y = abs(ball.vel.y) * WALL_BOUNCE
    elif ball.pos.y + BALL_RADIUS > TABLE_RECT.bottom:
        ball.pos.y = TABLE_RECT.bottom - BALL_RADIUS
        ball.vel.y = -abs(ball.vel.y) * WALL_BOUNCE


def place_cue_ball(state: GameState) -> None:
    cue = cue_ball(state)
    cue.active = True
    cue.pos = CUE_START_POS.copy()
    cue.vel.update(0, 0)

    min_dist = BALL_RADIUS * 2
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
    min_dist = BALL_RADIUS * 2

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

        for pocket in POCKETS:
            if ball.pos.distance_to(pocket) > POCKET_RADIUS - 3:
                continue

            if ball.is_cue:
                state.fouls += 1
                place_cue_ball(state)
            else:
                state.balls_pocketed += 1
                ball.active = False
                ball.vel.update(0, 0)
            break


def settle_round_if_needed(state: GameState) -> None:
    if is_any_ball_moving(state):
        return

    for ball in state.balls:
        if ball.active:
            ball.vel.update(0, 0)

    if target_balls_remaining(state) == 0:
        state.phase = PHASE_ROUND_OVER
        state.round_message = "Target cleared. Press R to restart."
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


def current_shot_power(state: GameState, mouse_pos: tuple[int, int]) -> float:
    pull = cue_ball(state).pos - pygame.Vector2(mouse_pos)
    return min(pull.length() * SHOT_POWER_SCALE, MAX_SHOT_SPEED)


def strike_cue_ball(state: GameState, mouse_pos: tuple[int, int]) -> None:
    cue = cue_ball(state)
    pull = cue.pos - pygame.Vector2(mouse_pos)
    if pull.length_squared() == 0:
        return

    shot_speed = min(pull.length() * SHOT_POWER_SCALE, MAX_SHOT_SPEED)
    if shot_speed < MIN_SHOT_SPEED:
        return

    cue.vel = pull.normalize() * shot_speed
    state.shot_count += 1
    state.phase = PHASE_MOVING


def handle_event(state: GameState, event: pygame.event.Event, mouse_pos: tuple[int, int]) -> bool:
    if event.type == pygame.QUIT:
        return False

    if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
        reset_round(state)
        return True

    if state.phase != PHASE_AIM:
        return True

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        state.charging = True
    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        if state.charging:
            strike_cue_ball(state, mouse_pos)
        state.charging = False

    return True


def draw_table(screen: pygame.Surface) -> None:
    screen.fill(BG_COLOR)
    pygame.draw.rect(screen, RAIL_COLOR, TABLE_RECT.inflate(28, 28), border_radius=22)
    pygame.draw.rect(screen, TABLE_COLOR, TABLE_RECT, border_radius=18)

    for pocket in POCKETS:
        pygame.draw.circle(screen, POCKET_COLOR, pocket, POCKET_RADIUS)


def draw_balls(screen: pygame.Surface, state: GameState) -> None:
    for ball in state.balls:
        if not ball.active:
            continue
        pygame.draw.circle(
            screen,
            ball.color,
            (int(ball.pos.x), int(ball.pos.y)),
            BALL_RADIUS,
        )


def draw_aim_guide(screen: pygame.Surface, state: GameState, mouse_pos: tuple[int, int]) -> None:
    if state.phase != PHASE_AIM:
        return

    cue = cue_ball(state)
    pull = cue.pos - pygame.Vector2(mouse_pos)
    if pull.length_squared() == 0:
        return

    guide_len = min(140, pull.length())
    line_end = cue.pos + pull.normalize() * guide_len
    pygame.draw.line(
        screen,
        AIM_COLOR,
        (int(cue.pos.x), int(cue.pos.y)),
        (int(line_end.x), int(line_end.y)),
        2,
    )


def draw_power_bar(screen: pygame.Surface, state: GameState, mouse_pos: tuple[int, int]) -> None:
    bar_width = 240
    bar_height = 18
    bar_x = TABLE_RECT.left
    bar_y = HEIGHT - 35

    pygame.draw.rect(screen, BAR_BG, (bar_x, bar_y, bar_width, bar_height), border_radius=8)
    if not state.charging or state.phase != PHASE_AIM:
        return

    fill = int((current_shot_power(state, mouse_pos) / MAX_SHOT_SPEED) * bar_width)
    pygame.draw.rect(screen, BAR_FILL, (bar_x, bar_y, fill, bar_height), border_radius=8)


def draw_hud(screen: pygame.Surface, font: pygame.font.Font, state: GameState) -> None:
    if state.phase == PHASE_AIM:
        status = "Your turn"
    elif state.phase == PHASE_MOVING:
        status = "Balls moving"
    else:
        status = "Round over"

    hud = f"{status} | Shots: {state.shot_count} | Pocketed: {state.balls_pocketed} | Fouls: {state.fouls}"
    text_surf = font.render(hud, True, TEXT_COLOR)
    screen.blit(text_surf, (TABLE_RECT.left, 20))


def draw_round_overlay(
    screen: pygame.Surface,
    title_font: pygame.font.Font,
    body_font: pygame.font.Font,
    state: GameState,
) -> None:
    if state.phase != PHASE_ROUND_OVER:
        return

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill(OVERLAY_COLOR)
    screen.blit(overlay, (0, 0))

    title = title_font.render("Round Complete", True, TEXT_COLOR)
    message = body_font.render(state.round_message, True, TEXT_COLOR)

    title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 18))
    message_rect = message.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 18))
    screen.blit(title, title_rect)
    screen.blit(message, message_rect)


def render(
    screen: pygame.Surface,
    hud_font: pygame.font.Font,
    title_font: pygame.font.Font,
    state: GameState,
    mouse_pos: tuple[int, int],
) -> None:
    draw_table(screen)
    draw_balls(screen, state)
    draw_aim_guide(screen, state, mouse_pos)
    draw_power_bar(screen, state, mouse_pos)
    draw_hud(screen, hud_font, state)
    draw_round_overlay(screen, title_font, hud_font, state)
    pygame.display.flip()


def main() -> int:
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Billiard Simulator")
    clock = pygame.time.Clock()
    hud_font = pygame.font.SysFont("arial", 24)
    title_font = pygame.font.SysFont("arial", 34)

    state = create_initial_state()
    max_frames_raw = os.getenv("BILLIARD_MAX_FRAMES", "").strip()
    max_frames = int(max_frames_raw) if max_frames_raw.isdigit() else None
    frame_count = 0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            running = handle_event(state, event, mouse_pos)
            if not running:
                break

        update_physics(state, dt)
        render(screen, hud_font, title_font, state, mouse_pos)

        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            break

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
