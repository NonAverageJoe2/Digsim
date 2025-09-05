import pygame
from typing import Tuple, List

# ---------- Simple top-down shop (runs its own loop, returns when leaving) ----------

ROOM_TILES = (24, 16)   # width, height in tiles
TILE_SIZE  = 32
PLAYER_SIZE = (16, 16)
PLAYER_SPEED = 180.0
PLAYER_ACCEL = 1400.0
PLAYER_FRICTION = 1800.0

# Colors
WOOD_BASE   = (82, 62, 45)
WOOD_LIGHT  = (112, 88, 65)
WOOD_DARK   = (60, 45, 32)
WALL_COLOR  = (40, 30, 22)
BENCH_COLOR = (55, 40, 28)
UI_BG       = (0, 0, 0)
UI_FG       = (240, 240, 240)
LEAVE_BG    = (30, 30, 30)
LEAVE_FG    = (220, 220, 220)

def _make_wood_tile() -> pygame.Surface:
    """Create a small wood plank tile to blit across the floor."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE)).convert()
    surf.fill(WOOD_BASE)
    # subtle plank lines
    for y in range(4, TILE_SIZE, 8):
        pygame.draw.line(surf, WOOD_DARK, (0, y), (TILE_SIZE, y), 1)
        if y+1 < TILE_SIZE:
            pygame.draw.line(surf, WOOD_LIGHT, (0, y+1), (TILE_SIZE, y+1), 1)
    # few 'knots'
    for cx in (8, 24):
        pygame.draw.circle(surf, WOOD_DARK, (cx, 6), 2, 1)
        pygame.draw.circle(surf, WOOD_LIGHT, (cx, 6), 1, 1)
    return surf

def _tile_fill(dest: pygame.Surface, tile: pygame.Surface) -> None:
    """Fill the entire dest with the given tile surface."""
    tw, th = tile.get_size()
    w, h = dest.get_size()
    for y in range(0, h, th):
        for x in range(0, w, tw):
            dest.blit(tile, (x, y))

def _player_rect(center: Tuple[float, float]) -> pygame.Rect:
    w, h = PLAYER_SIZE
    return pygame.Rect(int(center[0] - w/2), int(center[1] - h/2), w, h)

def _resolve_collisions(rect: pygame.Rect, obstacles: List[pygame.Rect], vel: pygame.Vector2) -> Tuple[pygame.Rect, pygame.Vector2]:
    """Axis-separated collision resolution against static AABBs."""
    # X move
    moved = rect.move(int(round(vel.x)), 0)
    for ob in obstacles:
        if moved.colliderect(ob):
            if vel.x > 0:
                moved.right = ob.left
            elif vel.x < 0:
                moved.left = ob.right
            vel.x = 0
    rect = moved
    # Y move
    moved = rect.move(0, int(round(vel.y)))
    for ob in obstacles:
        if moved.colliderect(ob):
            if vel.y > 0:
                moved.bottom = ob.top
            elif vel.y < 0:
                moved.top = ob.bottom
            vel.y = 0
    return moved, vel

def _clamp_to_room(rect: pygame.Rect, room_px: Tuple[int, int]) -> pygame.Rect:
    w, h = room_px
    if rect.left < 0: rect.left = 0
    if rect.top < 0: rect.top = 0
    if rect.right > w: rect.right = w
    if rect.bottom > h: rect.bottom = h
    return rect

def run_shop(screen: pygame.Surface) -> None:
    """
    Blocks and runs a top-down wood shop scene.
    Returns to the caller (your world) when the user clicks 'Leave' or presses Esc.
    """
    clock = pygame.time.Clock()
    sw, sh = screen.get_size()
    room_px = (ROOM_TILES[0] * TILE_SIZE, ROOM_TILES[1] * TILE_SIZE)

    # Viewport: center the room if smaller than window; otherwise anchor top-left.
    view_offset = (max(0, (sw - room_px[0]) // 2), max(0, (sh - room_px[1]) // 2))

    # Build floor once
    floor = pygame.Surface(room_px).convert()
    wood_tile = _make_wood_tile()
    _tile_fill(floor, wood_tile)

    # Walls (simple 1-tile thick border)
    walls: List[pygame.Rect] = []
    walls.append(pygame.Rect(0, 0, room_px[0], TILE_SIZE))                    # top
    walls.append(pygame.Rect(0, room_px[1] - TILE_SIZE, room_px[0], TILE_SIZE))  # bottom
    walls.append(pygame.Rect(0, 0, TILE_SIZE, room_px[1]))                    # left
    walls.append(pygame.Rect(room_px[0] - TILE_SIZE, 0, TILE_SIZE, room_px[1]))  # right

    # Benches / counters (obstacles)
    benches: List[pygame.Rect] = [
        pygame.Rect(TILE_SIZE * 3, TILE_SIZE * 4, TILE_SIZE * 6, TILE_SIZE * 1),
        pygame.Rect(TILE_SIZE * 14, TILE_SIZE * 6, TILE_SIZE * 6, TILE_SIZE * 1),
        pygame.Rect(TILE_SIZE * 6, TILE_SIZE * 10, TILE_SIZE * 10, TILE_SIZE * 1),
    ]
    obstacles = walls + benches

    # Leave button
    font = pygame.font.SysFont(None, 24)
    leave_text = font.render("Leave Shop (Esc)", True, LEAVE_FG)
    leave_pad = 8
    leave_rect = pygame.Rect(view_offset[0] + 10, view_offset[1] + 10, leave_text.get_width() + leave_pad*2, leave_text.get_height() + leave_pad*2)

    # Player
    p_rect = _player_rect((room_px[0] * 0.5, room_px[1] * 0.75))
    vel = pygame.Vector2(0, 0)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Bubble up quit to caller
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if leave_rect.collidepoint(mx, my):
                    return

        # Input
        keys = pygame.key.get_pressed()
        dir_x = (1 if keys[pygame.K_RIGHT] or keys[pygame.K_d] else 0) - (1 if keys[pygame.K_LEFT] or keys[pygame.K_a] else 0)
        dir_y = (1 if keys[pygame.K_DOWN] or keys[pygame.K_s] else 0) - (1 if keys[pygame.K_UP] or keys[pygame.K_w] else 0)
        move_dir = pygame.Vector2(dir_x, dir_y)
        if move_dir.length_squared() > 0:
            move_dir = move_dir.normalize()
            target = move_dir * PLAYER_SPEED
            # accelerate toward target
            dv = target - vel
            step = PLAYER_ACCEL * dt
            if dv.length() <= step:
                vel = target
            else:
                vel += dv.normalize() * step
        else:
            # friction to stop
            speed = vel.length()
            if speed > 0:
                drop = PLAYER_FRICTION * dt
                speed = max(0.0, speed - drop)
                vel = vel.normalize() * speed if speed > 0 else pygame.Vector2(0, 0)

        # Move & collide
        p_rect, vel = _resolve_collisions(p_rect, obstacles, vel * dt)
        p_rect = _clamp_to_room(p_rect, room_px)

        # -------- Draw --------
        screen.fill((0, 0, 0))

        # Floor
        screen.blit(floor, view_offset)

        # Benches
        for b in benches:
            pygame.draw.rect(screen, BENCH_COLOR, b.move(view_offset))

        # Walls
        for w in walls:
            pygame.draw.rect(screen, WALL_COLOR, w.move(view_offset))

        # Player (top-down marker)
        pr = p_rect.move(view_offset)
        pygame.draw.rect(screen, (240, 230, 120), pr)  # simple rectangle avatar
        # small direction dot
        pygame.draw.circle(screen, (20, 20, 20), (pr.centerx, pr.top + 3), 2)

        # UI: Leave button
        pygame.draw.rect(screen, LEAVE_BG, leave_rect, border_radius=6)
        screen.blit(leave_text, (leave_rect.x + leave_pad, leave_rect.y + leave_pad))

        # Caption
        cap = font.render("Wood Shop (Top-Down)", True, UI_FG)
        screen.blit(cap, (view_offset[0] + 12, view_offset[1] + leave_rect.height + 16))

        pygame.display.flip()
