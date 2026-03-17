import pygame
from constants import TABLE_RECT, WIDTH

# ????????? ????????????? ?????????? ???? ?? ??????
def power_bar_geometry(screen_size: tuple[int, int]) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
    """
    ?????????? (overlay_rect_abs, bar_rect_rel, bar_rect_abs)
    overlay_rect_abs ? ?????????? ?????????? ???????,
    bar_rect_rel ? ?????????? ???? ?????? ???????,
    bar_rect_abs ? ?????????? ?????????? ???? ?? ??????.
    """
    screen_w, screen_h = screen_size
    margin = 18
    bar_width = 18
    bar_height = int(screen_h * 0.7)

    overlay_rect = pygame.Rect(
        margin,
        (screen_h - bar_height) // 2,
        bar_width + 220,
        bar_height + 48,
    )
    bar_rect_rel = pygame.Rect(36, 24, bar_width, bar_height)
    bar_rect_abs = bar_rect_rel.move(overlay_rect.topleft)
    return overlay_rect, bar_rect_rel, bar_rect_abs


def calibration_panel_geometry() -> tuple[pygame.Rect, list[pygame.Rect], pygame.Rect]:
    """
    Layout for calibration text boxes and Apply button placed to the right of the table.
    Coordinates are in base canvas space.
    """
    panel_w = 220
    field_h = 34
    gap = 18
    padding = 12

    x = min(WIDTH - panel_w - 20, TABLE_RECT.right + 30)
    y = TABLE_RECT.top

    field_rects: list[pygame.Rect] = []
    for i in range(8):
        field_rects.append(
            pygame.Rect(
                x + padding,
                y + padding + i * (field_h + gap),
                panel_w - padding * 2,
                field_h,
            )
        )

    button_w = 140
    button_h = 32
    panel_h = padding * 2 + (field_h + gap) * 8 + button_h + 6 - gap  # последний ряд без лишнего зазора
    panel_rect = pygame.Rect(x, y, panel_w, panel_h)

    apply_rect = pygame.Rect(
        x + padding,
        panel_rect.bottom - padding - button_h,
        button_w,
        button_h,
    )

    return panel_rect, field_rects, apply_rect
