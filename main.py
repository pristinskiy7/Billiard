import os

import pygame

from constants import FPS, HEIGHT, WIDTH
from input import handle_event
from models import create_initial_state
from physics import update_physics
from render import render


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
