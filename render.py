import pygame

from constants import (
    AIM_COLOR,
    BALL_RADIUS,
    BALL_RADIUS_MM,
    BAR_BG,
    BAR_FILL,
    BG_COLOR,
    CORNER_POCKET_DIAMETER_MM,
    CORNER_POCKET_RADIUS_MM,
    CORNER_POCKET_DEPTH_MM,
    CORNER_POCKET_WIDTH_MM,
    GUIDE_LENGTH,
    HEIGHT,
    MAX_FOULS,
    MAX_SHOT_SPEED,
    OVERLAY_COLOR,
    POCKET_COLOR,
    RAIL_COLOR,
    RAIL_THICKNESS_PX,
    SIDE_POCKET_WIDTH_MM,
    TABLE_COLOR,
    TABLE_HEIGHT_MM,
    TABLE_RECT,
    TABLE_SCALE,
    TABLE_WIDTH_MM,
    TEXT_COLOR,
    WIDTH,
    PHASE_AIM,
    PHASE_MOVING,
    PHASE_ROUND_OVER,
)
from geometry import mm_rect_to_screen, mm_to_px, table_to_screen
from input import aim_vector, current_shot_power
from models import GameState, cue_ball


def draw_corner_pocket_geometry(screen: pygame.Surface) -> None:
    pocket_radius_px = mm_to_px(CORNER_POCKET_RADIUS_MM)
    corridor_projection_px = mm_to_px(CORNER_POCKET_WIDTH_MM / (2**0.5))
    corridor_normal_px = mm_to_px(CORNER_POCKET_DEPTH_MM / (2**0.5))

    corner_specs = [
        (TABLE_RECT.left, TABLE_RECT.top, 1, 1),
        (TABLE_RECT.right, TABLE_RECT.top, -1, 1),
        (TABLE_RECT.left, TABLE_RECT.bottom, 1, -1),
        (TABLE_RECT.right, TABLE_RECT.bottom, -1, -1),
    ]

    for corner_x, corner_y, sx, sy in corner_specs:
        rail_top_end = (
            round(corner_x + sx * corridor_projection_px),
            round(corner_y),
        )
        rail_side_end = (
            round(corner_x),
            round(corner_y + sy * corridor_projection_px),
        )
        pocket_top_end = (
            round(rail_top_end[0] - sx * corridor_normal_px),
            round(rail_top_end[1] - sy * corridor_normal_px),
        )
        pocket_side_end = (
            round(rail_side_end[0] - sx * corridor_normal_px),
            round(rail_side_end[1] - sy * corridor_normal_px),
        )
        far_side_midpoint = pygame.Vector2(
            (pocket_top_end[0] + pocket_side_end[0]) * 0.5,
            (pocket_top_end[1] + pocket_side_end[1]) * 0.5,
        )
        outward_normal = pygame.Vector2(-sx, -sy).normalize()
        pocket_center = far_side_midpoint + outward_normal * pocket_radius_px

        pygame.draw.circle(screen, POCKET_COLOR, pocket_center, pocket_radius_px)

        pygame.draw.polygon(
            screen,
            TABLE_COLOR,
            [
                rail_top_end,
                rail_side_end,
                pocket_side_end,
                pocket_top_end,
            ],
        )


def draw_corner_pockets(screen: pygame.Surface) -> None:
    draw_corner_pocket_geometry(screen)


def draw_side_pockets(screen: pygame.Surface) -> None:
    pocket_radius_px = mm_to_px(CORNER_POCKET_RADIUS_MM)
    side_half_width_px = mm_to_px(SIDE_POCKET_WIDTH_MM * 0.5)

    side_specs = [
        (TABLE_RECT.centerx, TABLE_RECT.top, -1),
        (TABLE_RECT.centerx, TABLE_RECT.bottom, 1),
    ]

    for center_x, rail_y, direction in side_specs:
        pocket_center = pygame.Vector2(center_x, rail_y + direction * pocket_radius_px)
        pygame.draw.circle(screen, POCKET_COLOR, pocket_center, pocket_radius_px)

        cloth_line = [
            (center_x - side_half_width_px, rail_y),
            (center_x + side_half_width_px, rail_y),
            (center_x + side_half_width_px, rail_y - direction * 1),
            (center_x - side_half_width_px, rail_y - direction * 1),
        ]
        pygame.draw.polygon(screen, TABLE_COLOR, cloth_line)


def draw_table(screen: pygame.Surface) -> None:
    screen.fill(BG_COLOR)
    pygame.draw.rect(
        screen,
        RAIL_COLOR,
        TABLE_RECT.inflate(RAIL_THICKNESS_PX * 2, RAIL_THICKNESS_PX * 2),
        border_radius=22,
    )
    pygame.draw.rect(screen, TABLE_COLOR, TABLE_RECT, border_radius=18)

    draw_corner_pockets(screen)
    draw_side_pockets(screen)


def draw_balls(screen: pygame.Surface, state: GameState) -> None:
    for ball in state.balls:
        if not ball.active:
            continue
        pygame.draw.circle(screen, ball.color, table_to_screen(ball.pos), BALL_RADIUS)


def draw_aim_guide(screen: pygame.Surface, state: GameState, mouse_pos: tuple[int, int]) -> None:
    if state.phase != PHASE_AIM:
        return

    cue = cue_ball(state)
    direction = aim_vector(state, mouse_pos)
    if direction.length_squared() == 0:
        return

    guide_len = min(GUIDE_LENGTH, direction.length())
    line_end = cue.pos + direction.normalize() * guide_len
    pygame.draw.line(screen, AIM_COLOR, table_to_screen(cue.pos), table_to_screen(line_end), 2)
    pygame.draw.circle(screen, AIM_COLOR, table_to_screen(line_end), 4)


def draw_power_bar(screen: pygame.Surface, state: GameState, mouse_pos: tuple[int, int]) -> None:
    bar_width = 240
    bar_height = 18
    bar_x = TABLE_RECT.left
    bar_y = HEIGHT - 35

    pygame.draw.rect(screen, BAR_BG, (bar_x, bar_y, bar_width, bar_height), border_radius=8)
    power = current_shot_power(state) if state.phase == PHASE_AIM else 0.0
    fill = int((power / MAX_SHOT_SPEED) * bar_width)
    pygame.draw.rect(screen, BAR_FILL, (bar_x, bar_y, fill, bar_height), border_radius=8)

    # Bort tick marks
    if state.bort_speeds:
        for idx, speed in enumerate(state.bort_speeds, start=1):
            pos = bar_x + int(bar_width * min(speed / MAX_SHOT_SPEED, 1.0))
            pygame.draw.line(screen, AIM_COLOR, (pos, bar_y - 6), (pos, bar_y + bar_height + 6), 1)
            label = f"{idx}"
            screen.blit(
                pygame.font.SysFont("arial", 14).render(label, True, TEXT_COLOR),
                (pos - 5, bar_y - 22),
            )
    label = "Power (борта)"
    screen.blit(pygame.font.SysFont("arial", 14).render(label, True, TEXT_COLOR), (bar_x, bar_y - 22))


def draw_hud(screen: pygame.Surface, font: pygame.font.Font, state: GameState) -> None:
    if state.phase == PHASE_AIM:
        status = f"Player {state.current_player + 1} aim"
    elif state.phase == PHASE_MOVING:
        status = "Balls moving"
    else:
        status = state.round_title or "Round over"

    hud = (
        f"{status} | Score P1:{state.scores[0]} P2:{state.scores[1]} | "
        f"Shots: {state.shot_count} | Pocketed total: {state.balls_pocketed} | Fouls: {state.fouls}"
    )
    screen.blit(font.render(hud, True, TEXT_COLOR), (TABLE_RECT.left, 20))

    info = (
        state.info_message
        or "Hold 1+LMB to set cue. Hold 2 to charge, then LMB click to shoot. Ctrl+wheel zoom, Ctrl+LMB pan."
    )
    screen.blit(font.render(info, True, TEXT_COLOR), (TABLE_RECT.left, HEIGHT - 70))

    hint = f"Foul if cue misses contact. Penalty: one of your pocketed balls returns. {MAX_FOULS} fouls ends the round."
    screen.blit(font.render(hint, True, TEXT_COLOR), (TABLE_RECT.left, HEIGHT - 40))


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

    title = title_font.render(state.round_title or "Round Complete", True, TEXT_COLOR)
    message = body_font.render(state.round_message, True, TEXT_COLOR)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 18)))
    screen.blit(message, message.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 18)))


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
