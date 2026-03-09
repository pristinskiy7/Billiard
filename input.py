import pygame

from constants import MAX_PULL_DISTANCE, MAX_SHOT_SPEED, MIN_SHOT_SPEED, PHASE_AIM, PHASE_MOVING
from geometry import screen_to_table
from models import GameState, cue_ball, reset_round


def shot_pull_vector(state: GameState, mouse_pos: tuple[int, int]) -> pygame.Vector2:
    pull = cue_ball(state).pos - screen_to_table(mouse_pos)
    if pull.length_squared() == 0:
        return pygame.Vector2()
    if pull.length() > MAX_PULL_DISTANCE:
        pull.scale_to_length(MAX_PULL_DISTANCE)
    return pull


def current_shot_power(state: GameState, mouse_pos: tuple[int, int]) -> float:
    pull = shot_pull_vector(state, mouse_pos)
    normalized_pull = min(1.0, pull.length() / MAX_PULL_DISTANCE)
    return min((normalized_pull ** 1.15) * MAX_SHOT_SPEED, MAX_SHOT_SPEED)


def strike_cue_ball(state: GameState, mouse_pos: tuple[int, int]) -> None:
    cue = cue_ball(state)
    pull = shot_pull_vector(state, mouse_pos)
    if pull.length_squared() == 0:
        return

    normalized_pull = pull.length() / MAX_PULL_DISTANCE
    shot_speed = min((normalized_pull ** 1.15) * MAX_SHOT_SPEED, MAX_SHOT_SPEED)
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
