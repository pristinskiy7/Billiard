import pygame

from constants import BALL_RADIUS_MM, CHARGE_RATE, MAX_SHOT_SPEED, MIN_SHOT_SPEED, PHASE_AIM, PHASE_MOVING
from geometry import screen_to_table
from models import GameState, cue_ball, enter_calibration_mode, exit_calibration_mode, reset_round


def aim_vector(state: GameState, mouse_pos: tuple[int, int]) -> pygame.Vector2:
    return screen_to_table(mouse_pos) - cue_ball(state).pos


def current_shot_power(state: GameState) -> float:
    return min(state.charge_power, MAX_SHOT_SPEED)


def accumulate_charge(state: GameState, dt: float) -> None:
    if not state.charging:
        return
    state.charge_power = min(MAX_SHOT_SPEED, state.charge_power + CHARGE_RATE * dt)


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
    if event.type == pygame.KEYDOWN and event.key == pygame.K_2 and state.phase == PHASE_AIM:
        state.charging = True
        state.charge_power = 0.0
        return True
    if event.type == pygame.KEYUP and event.key == pygame.K_2:
        state.charging = False
        return True

    if state.phase != PHASE_AIM:
        return True

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if keys[pygame.K_1]:
            select_cue_ball(state, mouse_pos)
        else:
            strike_cue_ball(state, mouse_pos)

    return True
