import sys
import pygame

pygame.init()

WIDTH = 1000
HEIGHT = 600
FPS = 120

TABLE_MARGIN = 60
TABLE_RECT = pygame.Rect(
    TABLE_MARGIN,
    TABLE_MARGIN,
    WIDTH - TABLE_MARGIN * 2,
    HEIGHT - TABLE_MARGIN * 2,
)

BALL_RADIUS = 15
POCKET_RADIUS = 28

FRICTION = 230.0
MIN_SPEED = 8.0
WALL_BOUNCE = 0.92
BALL_COLLISION_DAMP = 0.98
SHOT_POWER_SCALE = 6.0
MAX_SHOT_SPEED = 1100.0
MIN_SHOT_SPEED = 25.0

BG_COLOR = (76, 52, 35)
TABLE_COLOR = (20, 120, 20)
RAIL_COLOR = (36, 86, 36)
BALL_COLOR = (245, 245, 245)
TARGET_BALL_COLOR = (220, 70, 70)
POCKET_COLOR = (18, 18, 18)
AIM_COLOR = (255, 232, 128)
BAR_BG = (30, 30, 30)
BAR_FILL = (255, 200, 40)
TEXT_COLOR = (245, 245, 245)

POCKETS = [
    pygame.Vector2(TABLE_RECT.left, TABLE_RECT.top),
    pygame.Vector2(TABLE_RECT.centerx, TABLE_RECT.top),
    pygame.Vector2(TABLE_RECT.right, TABLE_RECT.top),
    pygame.Vector2(TABLE_RECT.left, TABLE_RECT.bottom),
    pygame.Vector2(TABLE_RECT.centerx, TABLE_RECT.bottom),
    pygame.Vector2(TABLE_RECT.right, TABLE_RECT.bottom),
]

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Billiard Simulator")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 24)

cue_start_pos = pygame.Vector2(TABLE_RECT.left + 180, TABLE_RECT.centery)
target_start_pos = pygame.Vector2(TABLE_RECT.right - 220, TABLE_RECT.centery)

balls = [
    {
        "name": "cue",
        "pos": cue_start_pos.copy(),
        "vel": pygame.Vector2(0, 0),
        "color": BALL_COLOR,
        "active": True,
        "is_cue": True,
    },
    {
        "name": "target_1",
        "pos": target_start_pos.copy(),
        "vel": pygame.Vector2(0, 0),
        "color": TARGET_BALL_COLOR,
        "active": True,
        "is_cue": False,
    },
]

shot_count = 0
balls_pocketed = 0
fouls = 0
state = "aim"
charging = False


def cue_ball():
    return balls[0]


def is_any_ball_moving() -> bool:
    threshold = MIN_SPEED * MIN_SPEED
    for ball in balls:
        if ball["active"] and ball["vel"].length_squared() > threshold:
            return True
    return False


def handle_wall_bounce(ball) -> None:
    pos = ball["pos"]
    vel = ball["vel"]

    if pos.x - BALL_RADIUS < TABLE_RECT.left:
        pos.x = TABLE_RECT.left + BALL_RADIUS
        vel.x = abs(vel.x) * WALL_BOUNCE
    elif pos.x + BALL_RADIUS > TABLE_RECT.right:
        pos.x = TABLE_RECT.right - BALL_RADIUS
        vel.x = -abs(vel.x) * WALL_BOUNCE

    if pos.y - BALL_RADIUS < TABLE_RECT.top:
        pos.y = TABLE_RECT.top + BALL_RADIUS
        vel.y = abs(vel.y) * WALL_BOUNCE
    elif pos.y + BALL_RADIUS > TABLE_RECT.bottom:
        pos.y = TABLE_RECT.bottom - BALL_RADIUS
        vel.y = -abs(vel.y) * WALL_BOUNCE


def place_cue_ball() -> None:
    cue = cue_ball()
    cue["active"] = True
    cue["pos"] = cue_start_pos.copy()
    cue["vel"] = pygame.Vector2(0, 0)

    for ball in balls:
        if ball is cue or not ball["active"]:
            continue

        delta = ball["pos"] - cue["pos"]
        min_dist = BALL_RADIUS * 2
        if delta.length_squared() < min_dist * min_dist:
            if delta.length_squared() == 0:
                delta = pygame.Vector2(1, 0)
            ball["pos"] = cue["pos"] + delta.normalize() * (min_dist + 1)


def check_pockets() -> None:
    global balls_pocketed, fouls

    for ball in balls:
        if not ball["active"]:
            continue

        for pocket in POCKETS:
            if ball["pos"].distance_to(pocket) <= POCKET_RADIUS - 3:
                if ball["is_cue"]:
                    fouls += 1
                    place_cue_ball()
                else:
                    balls_pocketed += 1
                    ball["active"] = False
                    ball["vel"].update(0, 0)
                break


def update_ball(ball, dt: float) -> None:
    vel = ball["vel"]
    speed = vel.length()
    if speed <= 0:
        return

    ball["pos"].x += vel.x * dt
    ball["pos"].y += vel.y * dt
    handle_wall_bounce(ball)

    decel = FRICTION * dt
    new_speed = max(0.0, speed - decel)
    if new_speed < MIN_SPEED:
        vel.update(0, 0)
    else:
        vel.scale_to_length(new_speed)


def resolve_ball_collisions() -> None:
    for i in range(len(balls)):
        ball_a = balls[i]
        if not ball_a["active"]:
            continue

        for j in range(i + 1, len(balls)):
            ball_b = balls[j]
            if not ball_b["active"]:
                continue

            delta = ball_b["pos"] - ball_a["pos"]
            min_dist = BALL_RADIUS * 2
            dist_sq = delta.length_squared()

            if dist_sq == 0:
                delta = pygame.Vector2(1, 0)
                dist_sq = 1.0
            if dist_sq > min_dist * min_dist:
                continue

            dist = dist_sq ** 0.5
            normal = delta / dist
            overlap = min_dist - dist

            correction = normal * (overlap * 0.5)
            ball_a["pos"] -= correction
            ball_b["pos"] += correction

            v1n = ball_a["vel"].dot(normal)
            v2n = ball_b["vel"].dot(normal)
            rel = v1n - v2n
            if rel <= 0:
                continue

            ball_a["vel"] += (v2n - v1n) * normal
            ball_b["vel"] += (v1n - v2n) * normal
            ball_a["vel"] *= BALL_COLLISION_DAMP
            ball_b["vel"] *= BALL_COLLISION_DAMP


def current_shot_power(mouse_pos: tuple[int, int]) -> float:
    pull = cue_ball()["pos"] - pygame.Vector2(mouse_pos)
    return min(pull.length() * SHOT_POWER_SCALE, MAX_SHOT_SPEED)


running = True
while running:
    dt = clock.tick(FPS) / 1000.0
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and state == "aim":
            charging = True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if charging and state == "aim":
                cue = cue_ball()
                pull = cue["pos"] - pygame.Vector2(mouse_pos)
                if pull.length_squared() > 0:
                    shot_speed = min(pull.length() * SHOT_POWER_SCALE, MAX_SHOT_SPEED)
                    if shot_speed >= MIN_SHOT_SPEED:
                        cue["vel"] = pull.normalize() * shot_speed
                        shot_count += 1
                        state = "balls_moving"
            charging = False

    if state == "balls_moving":
        for ball in balls:
            if ball["active"]:
                update_ball(ball, dt)

        resolve_ball_collisions()
        check_pockets()

        if not is_any_ball_moving():
            for ball in balls:
                if ball["active"]:
                    ball["vel"].update(0, 0)
            state = "aim"
            charging = False

    screen.fill(BG_COLOR)
    pygame.draw.rect(screen, RAIL_COLOR, TABLE_RECT.inflate(28, 28), border_radius=22)
    pygame.draw.rect(screen, TABLE_COLOR, TABLE_RECT, border_radius=18)

    for pocket in POCKETS:
        pygame.draw.circle(screen, POCKET_COLOR, pocket, POCKET_RADIUS)

    for ball in balls:
        if not ball["active"]:
            continue
        pygame.draw.circle(
            screen,
            ball["color"],
            (int(ball["pos"].x), int(ball["pos"].y)),
            BALL_RADIUS,
        )

    if state == "aim":
        cue = cue_ball()
        guide_mouse = pygame.Vector2(mouse_pos)
        pull = cue["pos"] - guide_mouse
        if pull.length_squared() > 0:
            guide_len = min(140, pull.length())
            guide_vec = pull.normalize() * guide_len
            line_end = cue["pos"] + guide_vec
            pygame.draw.line(
                screen,
                AIM_COLOR,
                (int(cue["pos"].x), int(cue["pos"].y)),
                (int(line_end.x), int(line_end.y)),
                2,
            )

        power = current_shot_power(mouse_pos) if charging else 0.0
        bar_w = 240
        bar_h = 18
        bar_x = TABLE_RECT.left
        bar_y = HEIGHT - 35
        pygame.draw.rect(screen, BAR_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=8)
        if power > 0:
            fill = int((power / MAX_SHOT_SPEED) * bar_w)
            pygame.draw.rect(screen, BAR_FILL, (bar_x, bar_y, fill, bar_h), border_radius=8)

    status = "Your turn" if state == "aim" else "Balls moving"
    hud = f"{status} | Shots: {shot_count} | Pocketed: {balls_pocketed} | Fouls: {fouls}"
    text_surf = font.render(hud, True, TEXT_COLOR)
    screen.blit(text_surf, (TABLE_RECT.left, 20))

    pygame.display.flip()

pygame.quit()
sys.exit()
