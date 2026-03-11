import os

import pygame

from constants import FPS, HEIGHT, WIDTH
from input import accumulate_charge, handle_event
from models import create_initial_state
from physics import compute_bort_speeds, update_physics
from render import render


def main() -> int:
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    canvas = pygame.Surface((WIDTH, HEIGHT)).convert_alpha()
    base_size = canvas.get_size()
    pygame.display.set_caption("Billiard Simulator")
    clock = pygame.time.Clock()
    hud_font = pygame.font.SysFont("arial", 24)
    title_font = pygame.font.SysFont("arial", 34)
    zoom = 1.0
    ZOOM_MIN = 0.5
    ZOOM_MAX = 2.5
    ZOOM_STEP = 1.1
    pan = pygame.Vector2()
    panning = False
    pan_anchor = (0, 0)

    state = create_initial_state()
    state.bort_speeds = compute_bort_speeds()
    max_frames_raw = os.getenv("BILLIARD_MAX_FRAMES", "").strip()
    max_frames = int(max_frames_raw) if max_frames_raw.isdigit() else None
    frame_count = 0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        win_w, win_h = screen.get_size()
        scale = min(win_w / base_size[0], win_h / base_size[1]) * zoom
        scaled_w = int(base_size[0] * scale)
        scaled_h = int(base_size[1] * scale)
        offset_x = (win_w - scaled_w) // 2
        offset_y = (win_h - scaled_h) // 2

        raw_mouse = pygame.mouse.get_pos()
        mouse_pos = (
            (raw_mouse[0] - offset_x - pan.x) / scale,
            (raw_mouse[1] - offset_y - pan.y) / scale,
        )

        for event in pygame.event.get():
            mods = pygame.key.get_mods()
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                continue
            if event.type == pygame.MOUSEWHEEL and mods & pygame.KMOD_CTRL:
                zoom = max(ZOOM_MIN, min(ZOOM_MAX, zoom * (ZOOM_STEP ** event.y)))
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and (mods & pygame.KMOD_CTRL):
                panning = True
                pan_anchor = event.pos
                continue
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and panning:
                panning = False
                continue
            if event.type == pygame.MOUSEMOTION and panning:
                dx = event.pos[0] - pan_anchor[0]
                dy = event.pos[1] - pan_anchor[1]
                pan.update(pan.x + dx, pan.y + dy)
                pan_anchor = event.pos
                continue
            running = handle_event(state, event, mouse_pos)
            if not running:
                break

        accumulate_charge(state, dt)
        update_physics(state, dt)
        render(canvas, hud_font, title_font, state, mouse_pos)

        if screen.get_size() == canvas.get_size():
            screen.blit(canvas, (0, 0))
        else:
            scaled = pygame.transform.smoothscale(canvas, (scaled_w, scaled_h))
            screen.fill((0, 0, 0))
            screen.blit(scaled, (offset_x + pan.x, offset_y + pan.y))
        pygame.display.flip()

        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            break

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
