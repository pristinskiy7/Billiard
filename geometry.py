# geometry.py

import pygame

from constants import (
    CORNER_POCKET_DEPTH_MM,
    CORNER_POCKET_WIDTH_MM,
    SIDE_POCKET_WIDTH_MM,
    TABLE_HEIGHT_MM,
    TABLE_RECT,
    TABLE_SCALE,
    TABLE_WIDTH_MM,
)
from models import Ball


def mm_to_px(value_mm: float) -> int:
    return int(round(value_mm * TABLE_SCALE))


def table_to_screen(pos_mm: pygame.Vector2) -> tuple[int, int]:
    return (
        TABLE_RECT.left + mm_to_px(pos_mm.x),
        TABLE_RECT.top + mm_to_px(pos_mm.y),
    )


def screen_to_table(pos_px: tuple[int, int]) -> pygame.Vector2:
    return pygame.Vector2(
        (pos_px[0] - TABLE_RECT.left) / TABLE_SCALE,
        (pos_px[1] - TABLE_RECT.top) / TABLE_SCALE,
    )


def mm_rect_to_screen(x_mm: float, y_mm: float, width_mm: float, height_mm: float) -> pygame.Rect:
    return pygame.Rect(
        TABLE_RECT.left + mm_to_px(x_mm),
        TABLE_RECT.top + mm_to_px(y_mm),
        max(1, mm_to_px(width_mm)),
        max(1, mm_to_px(height_mm)),
    )


def is_in_top_corner_opening(ball: Ball) -> bool:
    return (
        ball.pos.x <= CORNER_POCKET_WIDTH_MM
        or ball.pos.x >= TABLE_WIDTH_MM - CORNER_POCKET_WIDTH_MM
        or abs(ball.pos.x - TABLE_WIDTH_MM / 2) <= SIDE_POCKET_WIDTH_MM * 0.5
    )


def is_in_bottom_corner_opening(ball: Ball) -> bool:
    return (
        ball.pos.x <= CORNER_POCKET_WIDTH_MM
        or ball.pos.x >= TABLE_WIDTH_MM - CORNER_POCKET_WIDTH_MM
        or abs(ball.pos.x - TABLE_WIDTH_MM / 2) <= SIDE_POCKET_WIDTH_MM * 0.5
    )


def is_in_left_corner_opening(ball: Ball) -> bool:
    return ball.pos.y <= CORNER_POCKET_WIDTH_MM or ball.pos.y >= TABLE_HEIGHT_MM - CORNER_POCKET_WIDTH_MM


def is_in_right_corner_opening(ball: Ball) -> bool:
    return ball.pos.y <= CORNER_POCKET_WIDTH_MM or ball.pos.y >= TABLE_HEIGHT_MM - CORNER_POCKET_WIDTH_MM


def is_ball_in_pocket_corridor(ball: Ball) -> bool:
    x = ball.pos.x
    y = ball.pos.y

    if x <= CORNER_POCKET_DEPTH_MM and (y <= CORNER_POCKET_WIDTH_MM or y >= TABLE_HEIGHT_MM - CORNER_POCKET_WIDTH_MM):
        return True
    if x >= TABLE_WIDTH_MM - CORNER_POCKET_DEPTH_MM and (
        y <= CORNER_POCKET_WIDTH_MM or y >= TABLE_HEIGHT_MM - CORNER_POCKET_WIDTH_MM
    ):
        return True
    if y <= CORNER_POCKET_DEPTH_MM and (
        x <= CORNER_POCKET_WIDTH_MM
        or x >= TABLE_WIDTH_MM - CORNER_POCKET_WIDTH_MM
        or abs(x - TABLE_WIDTH_MM / 2) <= SIDE_POCKET_WIDTH_MM * 0.5
    ):
        return True
    if y >= TABLE_HEIGHT_MM - CORNER_POCKET_DEPTH_MM and (
        x <= CORNER_POCKET_WIDTH_MM
        or x >= TABLE_WIDTH_MM - CORNER_POCKET_WIDTH_MM
        or abs(x - TABLE_WIDTH_MM / 2) <= SIDE_POCKET_WIDTH_MM * 0.5
    ):
        return True

    return False
