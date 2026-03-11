from dataclasses import dataclass, field
from copy import deepcopy

import pygame

from constants import (
    BALL_COLOR,
    BALL_DIAMETER_MM,
    BLACK_BALL_COLOR,
    BLACK_START_POS,
    MAX_FOULS,
    PHASE_AIM,
    PYRAMID_APEX_POS,
    TABLE_HEIGHT_MM,
    TABLE_WIDTH_MM,
)


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
    round_title: str = ""
    round_message: str = ""
    current_player: int = 0
    scores: list[int] = field(default_factory=lambda: [0, 0])
    pocketed_by_player: list[list[Ball]] = field(default_factory=lambda: [[], []])
    shot_had_contact: bool = False
    shot_pocketed: int = 0
    shot_foul: bool = False
    info_message: str = ""
    charge_power: float = 0.0
    bort_speeds: list[float] = field(default_factory=list)
    calibration_mode: bool = False


def create_balls() -> list[Ball]:
    balls = [
        Ball(
            name="0",
            pos=BLACK_START_POS.copy(),
            vel=pygame.Vector2(),
            color=BLACK_BALL_COLOR,
            is_cue=True,
        )
    ]

    spacing = BALL_DIAMETER_MM + 4.0
    ball_number = 1
    for col in range(5):
        for row in range(col + 1):
            row_offset = row - col / 2
            pos = pygame.Vector2(
                PYRAMID_APEX_POS.x + col * spacing,
                PYRAMID_APEX_POS.y + row_offset * spacing,
            )
            balls.append(
                Ball(
                    name=str(ball_number),
                    pos=pos,
                    vel=pygame.Vector2(),
                    color=BALL_COLOR,
                    is_cue=False,
                )
            )
            ball_number += 1

    return balls


def create_initial_state() -> GameState:
    return GameState(balls=create_balls())


def reset_round(state: GameState) -> None:
    state.balls = create_balls()
    state.shot_count = 0
    state.balls_pocketed = 0
    state.fouls = 0
    state.current_player = 0
    state.scores = [0, 0]
    state.pocketed_by_player = [[], []]
    state.info_message = ""
    state.phase = PHASE_AIM
    state.charging = False
    state.round_title = ""
    state.round_message = ""
    state.shot_had_contact = False
    state.shot_pocketed = 0
    state.shot_foul = False
    state.charge_power = 0.0
    state.calibration_mode = False
    if hasattr(state, "_saved_state"):
        delattr(state, "_saved_state")


def cue_ball(state: GameState) -> Ball:
    for ball in state.balls:
        if ball.is_cue:
            return ball
    # Fallback: promote the first active ball to be cue if flags got lost
    for ball in state.balls:
        if ball.active:
            ball.is_cue = True
            return ball
    return state.balls[0]


def target_balls_remaining(state: GameState) -> int:
    return sum(1 for ball in state.balls if not ball.is_cue and ball.active)


def is_any_ball_moving(state: GameState, min_speed_sq: float) -> bool:
    return any(ball.active and ball.vel.length_squared() > min_speed_sq for ball in state.balls)


def is_round_lost(state: GameState) -> bool:
    return state.fouls >= MAX_FOULS


def enter_calibration_mode(state: GameState) -> None:
    if state.calibration_mode:
        return
    state._saved_state = deepcopy(state)
    center = pygame.Vector2(TABLE_WIDTH_MM * 0.5, TABLE_HEIGHT_MM * 0.5)
    state.balls = [
        Ball(
            name="C",
            pos=center,
            vel=pygame.Vector2(),
            color=BALL_COLOR,
            is_cue=True,
        )
    ]
    state.shot_count = 0
    state.balls_pocketed = 0
    state.fouls = 0
    state.scores = [0, 0]
    state.pocketed_by_player = [[], []]
    state.phase = PHASE_AIM
    state.charging = False
    state.round_title = ""
    state.round_message = ""
    state.shot_had_contact = False
    state.shot_pocketed = 0
    state.shot_foul = False
    state.charge_power = 0.0
    state.info_message = "Режим настройки силы: один шар на столе. Нажмите S чтобы выйти."
    state.calibration_mode = True


def exit_calibration_mode(state: GameState) -> None:
    if not state.calibration_mode:
        return
    if hasattr(state, "_saved_state"):
        saved: GameState = state._saved_state
        state.balls = saved.balls
        state.shot_count = saved.shot_count
        state.balls_pocketed = saved.balls_pocketed
        state.fouls = saved.fouls
        state.phase = saved.phase
        state.charging = saved.charging
        state.round_title = saved.round_title
        state.round_message = saved.round_message
        state.current_player = saved.current_player
        state.scores = saved.scores
        state.pocketed_by_player = saved.pocketed_by_player
        state.shot_had_contact = saved.shot_had_contact
        state.shot_pocketed = saved.shot_pocketed
        state.shot_foul = saved.shot_foul
        state.info_message = saved.info_message
        state.charge_power = saved.charge_power
        state.bort_speeds = saved.bort_speeds
        delattr(state, "_saved_state")
    state.calibration_mode = False
