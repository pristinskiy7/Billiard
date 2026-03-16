# render.py

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
from ui import power_bar_geometry, calibration_panel_geometry


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
    # Горизонтальный индикатор на столе отключён, используется экранный вертикальный оверлей.
    return


def draw_power_overlay_screen(screen: pygame.Surface, font: pygame.font.Font, state: GameState) -> None:
    overlay_rect, bar_rect_rel, _ = power_bar_geometry(screen.get_size())
    bar_width = bar_rect_rel.width
    bar_height = bar_rect_rel.height
    x, y = overlay_rect.topleft

    overlay = pygame.Surface(overlay_rect.size, pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 90))

    bar_rect = bar_rect_rel.copy()
    pygame.draw.rect(overlay, BAR_BG, bar_rect, border_radius=6)
    label_left_x = bar_rect.left - 18

    base_speed = MAX_SHOT_SPEED
    power_units = (current_shot_power(state) / base_speed) if state.phase == PHASE_AIM else 0.0
    fill_height = int(bar_height * min(1.0, power_units))
    if fill_height > 0:
        fill_rect = pygame.Rect(bar_rect.left, bar_rect.bottom - fill_height, bar_width, fill_height)
        pygame.draw.rect(overlay, BAR_FILL, fill_rect, border_radius=6)

    # Indicator scale: main marks 0-4 with 10 minor ticks per interval.
    tick_font = pygame.font.SysFont('arial', 14)

    for major in range(5):
        ratio = major / 4.0
        pos_y = bar_rect.bottom - int(bar_height * ratio)
        pygame.draw.line(overlay, AIM_COLOR, (bar_rect.left - 12, pos_y), (bar_rect.right + 12, pos_y), 2)

        number = tick_font.render(str(major), True, TEXT_COLOR)
        overlay.blit(number, (label_left_x - number.get_width(), pos_y - number.get_height() // 2))

    for interval_start in range(4):
        for step in range(1, 10):
            ratio = (interval_start + step / 10.0) / 4.0
            pos_y = bar_rect.bottom - int(bar_height * ratio)
            pygame.draw.line(overlay, AIM_COLOR, (bar_rect.left - 8, pos_y), (bar_rect.left - 2, pos_y), 1)
            pygame.draw.line(overlay, AIM_COLOR, (bar_rect.right + 2, pos_y), (bar_rect.right + 8, pos_y), 1)

    screen.blit(overlay, (x, y))


def draw_calibration_panel(screen: pygame.Surface, font: pygame.font.Font, state: GameState) -> None:
    panel_rect, field_rects, apply_rect = calibration_panel_geometry()
    small_font = pygame.font.SysFont("arial", 18)

    pygame.draw.rect(screen, (24, 24, 24), panel_rect, border_radius=8)
    pygame.draw.rect(screen, (80, 80, 80), panel_rect, width=2, border_radius=8)

    labels = [
        "Метка 4 (мм/с)",
        "Метка 3 (мм/с)",
        "Метка 2 (мм/с)",
        "Метка 1 (мм/с)",
        "Произвольная позиция (мм/с)",
        "Коэффициент торможения",
        "Восстановление борта",
        "Потеря энергии шаров",
    ]

    for idx, rect in enumerate(field_rects):
        label = labels[idx]
        label_surf = small_font.render(label, True, TEXT_COLOR)
        screen.blit(label_surf, (rect.x, rect.y - label_surf.get_height() - 2))

        pygame.draw.rect(screen, BAR_BG, rect, border_radius=4)
        if state.calibration_active_field == idx:
            pygame.draw.rect(screen, AIM_COLOR, rect, width=2, border_radius=4)
        else:
            pygame.draw.rect(screen, (120, 120, 120), rect, width=1, border_radius=4)

        value = state.calibration_inputs[idx] if idx < len(state.calibration_inputs) else ""
        text_surf = small_font.render(value, True, TEXT_COLOR)
        screen.blit(text_surf, (rect.x + 6, rect.y + (rect.height - text_surf.get_height()) // 2))

    button_color = BAR_FILL if state.calibration_dirty else AIM_COLOR
    pygame.draw.rect(screen, button_color, apply_rect, border_radius=6)
    pygame.draw.rect(screen, (40, 40, 40), apply_rect, width=2, border_radius=6)
    btn_text = small_font.render("Применить", True, (10, 10, 10))
    screen.blit(btn_text, (apply_rect.centerx - btn_text.get_width() // 2, apply_rect.centery - btn_text.get_height() // 2))

def draw_hud(screen: pygame.Surface, font: pygame.font.Font, state: GameState) -> None:
    if state.phase == PHASE_AIM:
        status = f"Игрок {state.current_player + 1} прицеливается"
    elif state.phase == PHASE_MOVING:
        status = "Шары движутся"
    else:
        status = state.round_title or "Раунд окончен"

    hud = (
        f"{status} | Счёт И1:{state.scores[0]} И2:{state.scores[1]} | "
        f"Удары: {state.shot_count} | Забито всего: {state.balls_pocketed} | Фолы: {state.fouls}"
    )
    screen.blit(font.render(hud, True, TEXT_COLOR), (TABLE_RECT.left, 20))

    info = (
        state.info_message
        or "1+ЛКМ — выбрать биток. Держите 2 — заряд, затем ЛКМ — удар. Ctrl+колесо — зум, Ctrl+ЛКМ — панорама."
    )
    screen.blit(font.render(info, True, TEXT_COLOR), (TABLE_RECT.left, HEIGHT - 70))

    hint = (
        f"Фол, если биток не касается шаров. Штраф: один из ваших забитых шаров возвращается. {MAX_FOULS} фолов завершают раунд."
    )
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

    title = title_font.render(state.round_title or "Раунд завершён", True, TEXT_COLOR)
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
    if state.calibration_mode:
        draw_calibration_panel(screen, hud_font, state)
    draw_hud(screen, hud_font, state)
    draw_round_overlay(screen, title_font, hud_font, state)
