# input.py

import pygame

from constants import BALL_RADIUS_MM, MAX_SHOT_SPEED, MIN_SHOT_SPEED, PHASE_AIM, PHASE_MOVING
from geometry import screen_to_table
from models import (
    GameState,
    cue_ball,
    enter_calibration_mode,
    exit_calibration_mode,
    reset_round,
    save_calibration,
)
from ui import power_bar_geometry, calibration_panel_geometry


def aim_vector(state: GameState, mouse_pos: tuple[int, int]) -> pygame.Vector2:
    return screen_to_table(mouse_pos) - cue_ball(state).pos


def current_shot_power(state: GameState) -> float:
    return state.charge_power


def power_ratio_from_speed(state: GameState, speed: float) -> float:
    """
    Обратное преобразование: скорость -> доля шкалы (0..1) с учётом
    фиксированных по высоте сегментов A-B, B-C, C-D, D-E.
    """
    speeds = [
        0.0,
        state.power_marks[1] if state.power_marks else 1500.0,  # B
        state.power_marks[2] if state.power_marks else 2100.0,  # C
        state.power_marks[3] if state.power_marks else 2600.0,  # D
        state.power_marks[4] if state.power_marks else 3100.0,  # E
    ]

    speed = max(0.0, min(speed, speeds[-1]))

    segments = [
        (0.00, 0.25, speeds[0], speeds[1]),  # A-B
        (0.25, 0.50, speeds[1], speeds[2]),  # B-C
        (0.50, 0.75, speeds[2], speeds[3]),  # C-D
        (0.75, 1.00, speeds[3], speeds[4]),  # D-E
    ]

    for start, end, v0, v1 in segments:
        if speed <= v1 or v1 == v0:
            if v1 == v0:
                return end
            t = (speed - v0) / (v1 - v0)
            return start + (end - start) * t
    return 1.0


def _set_power_from_bar_click(state: GameState, click_pos: tuple[int, int], screen_size: tuple[int, int]) -> bool:
    """
    Устанавливает силу удара по клику в вертикальный индикатор.
    click_pos — экранные координаты (event.pos).
    Возвращает True, если клик был по шкале и сила выставлена.
    """
    _, bar_rect_rel, bar_rect_abs = power_bar_geometry(screen_size)
    if not bar_rect_abs.collidepoint(click_pos):
        return False

    ratio_total = (bar_rect_abs.bottom - click_pos[1]) / bar_rect_rel.height
    ratio_total = max(0.0, min(1.0, ratio_total))
    state.charge_power = power_speed_from_ratio(state, ratio_total)
    return True


def power_speed_from_ratio(state: GameState, ratio: float) -> float:
    """
    Преобразует общую долю по шкале (0..1) в скорость удара с учётом
    четырёх линейных сегментов A-B, B-C, C-D, D-E одинаковой высоты.
    Диапазоны значений по сегментам (мм/с):
      A-B: 0 → 1500
      B-C: 1500 → 2100
      C-D: 2100 → 2600
      D-E: 2600 → 3100
    Значения в точках B–E могут быть скорректированы калибровкой
    (power_marks[1..4]), но визуальные сегменты остаются равными.
    """
    ratio = max(0.0, min(1.0, ratio))

    # Опорные скорости в точках A..E (A всегда 0).
    speeds = [
        0.0,
        state.power_marks[1] if state.power_marks else 1500.0,  # B
        state.power_marks[2] if state.power_marks else 2100.0,  # C
        state.power_marks[3] if state.power_marks else 2600.0,  # D
        state.power_marks[4] if state.power_marks else 3100.0,  # E
    ]

    segments = [
        (0.00, 0.25, speeds[0], speeds[1]),  # A-B
        (0.25, 0.50, speeds[1], speeds[2]),  # B-C
        (0.50, 0.75, speeds[2], speeds[3]),  # C-D
        (0.75, 1.00, speeds[3], speeds[4]),  # D-E
    ]

    for start, end, v0, v1 in segments:
        if ratio <= end:
            t = (ratio - start) / (end - start) if end > start else 0.0
            return v0 + (v1 - v0) * t
    return speeds[-1]


def _apply_calibration_inputs(state: GameState) -> None:
    try:
        mark_b = float(state.calibration_inputs[0])
        mark_c = float(state.calibration_inputs[1])
        mark_d = float(state.calibration_inputs[2])
        mark_e = float(state.calibration_inputs[3])
        custom = float(state.calibration_inputs[4])
        friction = float(state.calibration_inputs[5])
        wall = float(state.calibration_inputs[6])
        collision = float(state.calibration_inputs[7])
    except (ValueError, IndexError):
        return

    state.power_marks = [0.0, mark_b, mark_c, mark_d, mark_e]
    state.custom_power = max(0.0, custom)
    state.charge_power = state.custom_power  # заполняем индикатор и используем это значение для следующего удара
    state.friction = max(0.0, friction)
    state.wall_bounce = max(0.0, wall)
    state.collision_loss = max(0.0, collision)
    # Normalize input strings to tidy formatting
    state.calibration_inputs = [
        f"{mark_b:.1f}",
        f"{mark_c:.1f}",
        f"{mark_d:.1f}",
        f"{mark_e:.1f}",
        f"{state.custom_power:.1f}",
        f"{state.friction:.2f}",
        f"{state.wall_bounce:.3f}",
        f"{state.collision_loss:.3f}",
    ]
    state.calibration_dirty = False
    save_calibration(state)


def _handle_calibration_ui(state: GameState, event: pygame.event.Event, mouse_pos: tuple[int, int]) -> bool:
    panel_rect, field_rects, apply_rect = calibration_panel_geometry()

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        for idx, rect in enumerate(field_rects):
            if rect.collidepoint(mouse_pos):
                state.calibration_active_field = idx
                return True
        if apply_rect.collidepoint(mouse_pos):
            _apply_calibration_inputs(state)
            return True
        state.calibration_active_field = None
        return False

    if event.type == pygame.KEYDOWN and state.calibration_active_field is not None:
        idx = state.calibration_active_field
        if event.key == pygame.K_TAB:
            state.calibration_active_field = (idx + 1) % len(field_rects)
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            _apply_calibration_inputs(state)
            return True
        if event.key == pygame.K_BACKSPACE:
            state.calibration_inputs[idx] = state.calibration_inputs[idx][:-1]
            state.calibration_dirty = True
            return True
        # Accept digits, dot and minus
        ch = event.unicode
        if ch and (ch.isdigit() or ch in ".-"):
            state.calibration_inputs[idx] += ch
            state.calibration_dirty = True
            return True
    return False


def accumulate_charge(state: GameState, dt: float) -> None:
    # Режим "удерживать 2 для зарядки" больше не используется; сила ставится кликом.
    # Оставляем функцию для совместимости вызова в main, но она ничего не делает.
    return


def strike_cue_ball(state: GameState, mouse_pos: tuple[int, int]) -> None:
    cue = cue_ball(state)
    direction = aim_vector(state, mouse_pos)
    if direction.length_squared() == 0:
        return

    shot_speed = current_shot_power(state)
    if shot_speed < MIN_SHOT_SPEED:
        return

    cue.vel = direction.normalize() * shot_speed
    state.charging = False
    state.shot_count += 1
    state.shot_had_contact = False
    state.shot_pocketed = 0
    state.shot_foul = False
    state.charge_power = 0.0
    state.phase = PHASE_MOVING


def select_cue_ball(state: GameState, mouse_pos: tuple[int, int]) -> None:
    if state.phase != PHASE_AIM:
        return

    table_pos = screen_to_table(mouse_pos)
    for ball in state.balls:
        if not ball.active:
            continue
        if (ball.pos - table_pos).length_squared() <= (BALL_RADIUS_MM * 0.6) ** 2:
            for other in state.balls:
                other.is_cue = False
            ball.is_cue = True
            return


def handle_event(state: GameState, event: pygame.event.Event, mouse_pos: tuple[int, int]) -> bool:
    keys = pygame.key.get_pressed()

    if event.type == pygame.QUIT:
        return False

    if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
        reset_round(state)
        return True
    if event.type == pygame.KEYDOWN and event.key == pygame.K_s:
        if state.calibration_mode:
            exit_calibration_mode(state)
        else:
            enter_calibration_mode(state)
        return True
    if state.calibration_mode:
        if _handle_calibration_ui(state, event, mouse_pos):
            return True
    if state.phase != PHASE_AIM:
        return True

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        # С зажатой клавишей "2" клик по шкале ставит силу удара.
        if keys[pygame.K_2]:
            screen_size = pygame.display.get_surface().get_size()
            if _set_power_from_bar_click(state, event.pos, screen_size):
                return True

        if keys[pygame.K_1]:
            select_cue_ball(state, mouse_pos)
        else:
            strike_cue_ball(state, mouse_pos)

    return True
