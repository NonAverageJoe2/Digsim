import math
import random
import pygame

# --------------------------------- Config -------------------------------------
TILE_SIZE = 32
WORLD_WIDTH = 100
WORLD_HEIGHT = 100
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SKY_BLUE = (135, 206, 235)
SURFACE_LEVEL = 10

# Tile types
GRASS = 'grass'
DIRT = 'dirt'
STONE = 'stone'
GEM = 'gem'
BEDROCK = 'bedrock'
TILE_TYPES = [GRASS, DIRT, STONE, GEM, BEDROCK]

# Colors
TILE_COLORS = {
    GRASS: (34, 139, 34),
    DIRT: (139, 69, 19),
    STONE: (128, 128, 128),
    GEM: (128, 128, 128),
    BEDROCK: (10, 10, 10),
}
BG_COLORS = {
    GRASS: (34, 139, 34),
    DIRT: (101, 67, 33),
    STONE: (70, 70, 70),
    GEM: (70, 70, 70),
    BEDROCK: (0, 0, 0),
}

random.seed()


# --------------------------------- Helpers ------------------------------------
def create_tile_surface(base_color, detail_color=None):
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    surf.fill(base_color)
    if detail_color is None:
        return surf
    for _ in range(20):
        x = random.randint(0, TILE_SIZE - 4)
        y = random.randint(0, TILE_SIZE - 4)
        w = random.randint(1, 3)
        h = random.randint(1, 3)
        surf.fill(detail_color, pygame.Rect(x, y, w, h))
    return surf


def create_gem_surface():
    surf = create_tile_surface(TILE_COLORS[STONE], (100, 100, 100))
    pygame.draw.polygon(
        surf,
        (0, 255, 255),
        [
            (TILE_SIZE // 2, 4),
            (TILE_SIZE - 4, TILE_SIZE // 2),
            (TILE_SIZE // 2, TILE_SIZE - 4),
            (4, TILE_SIZE // 2),
        ],
        0,
    )
    return surf


def generate_world():
    world = [[None for _ in range(WORLD_HEIGHT)] for _ in range(WORLD_WIDTH)]
    background = [[SKY_BLUE for _ in range(WORLD_HEIGHT)] for _ in range(WORLD_WIDTH)]
    for x in range(WORLD_WIDTH):
        ground_y = SURFACE_LEVEL
        world[x][ground_y] = GRASS
        background[x][ground_y] = BG_COLORS[GRASS]

        dirt_depth = random.randint(9, 16)
        for y in range(ground_y + 1, ground_y + dirt_depth):
            world[x][y] = DIRT
            background[x][y] = BG_COLORS[DIRT]

        for y in range(ground_y + dirt_depth, WORLD_HEIGHT - 1):
            tile = GEM if random.random() < 0.05 else STONE
            world[x][y] = tile
            background[x][y] = BG_COLORS[tile]

        world[x][WORLD_HEIGHT - 1] = BEDROCK
        background[x][WORLD_HEIGHT - 1] = BG_COLORS[BEDROCK]
    return world, background


def solid_at(world, tx, ty):
    if 0 <= tx < WORLD_WIDTH and 0 <= ty < WORLD_HEIGHT:
        return world[tx][ty] is not None
    return True  # out of bounds is solid to keep you inside the map


def tiles_overlapping_aabb(rect):
    x_start = max(0, rect.left // TILE_SIZE - 1)
    x_end = min(WORLD_WIDTH, rect.right // TILE_SIZE + 2)
    y_start = max(0, rect.top // TILE_SIZE - 1)
    y_end = min(WORLD_HEIGHT, rect.bottom // TILE_SIZE + 2)
    return x_start, x_end, y_start, y_end


# ------------------------------ Effects ---------------------------------------
class MiningEffect:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.timer = 0
        self.duration = 15

    def update(self):
        self.timer += 1
        return self.timer >= self.duration

    def draw(self, surface, camera_x, camera_y):
        cx = self.x * TILE_SIZE - camera_x + TILE_SIZE // 2
        cy = self.y * TILE_SIZE - camera_y + TILE_SIZE // 2
        progress = self.timer / float(self.duration)
        length = progress * TILE_SIZE
        angles = [0, math.pi * 0.4, math.pi * 0.8, math.pi * 1.2, math.pi * 1.6]
        for ang in angles:
            dx = math.cos(ang) * length
            dy = math.sin(ang) * length
            pygame.draw.line(surface, (255, 255, 255), (cx, cy), (cx + dx, cy + dy), 2)


# ------------------------------- Main Loop ------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    tile_surfaces = {
        GRASS: create_tile_surface(TILE_COLORS[GRASS], (0, 100, 0)),
        DIRT: create_tile_surface(TILE_COLORS[DIRT], (160, 82, 45)),
        STONE: create_tile_surface(TILE_COLORS[STONE], (100, 100, 100)),
        GEM: create_gem_surface(),
        BEDROCK: create_tile_surface(TILE_COLORS[BEDROCK], (30, 30, 30)),
    }

    world, background = generate_world()

    # Player physics
    player = pygame.Rect(5 * TILE_SIZE, (SURFACE_LEVEL - 1) * TILE_SIZE, TILE_SIZE // 2, TILE_SIZE)
    vx, vy = 0.0, 0.0
    accel = 900.0
    max_speed = 180.0
    friction = 1200.0
    gravity = 1200.0
    max_fall = 600.0
    jump_speed = 380.0
    on_ground = False
    coyote_time = 0.08  # seconds after leaving ground where jump is still allowed
    coyote_left = 0.0

    camera_x = 0
    camera_y = 0
    mining_effects = []

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        # -------------------------- Input / events ---------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                tx = (mx + camera_x) // TILE_SIZE
                ty = (my + camera_y) // TILE_SIZE
                if 0 <= tx < WORLD_WIDTH and 0 <= ty < WORLD_HEIGHT:
                    tile = world[int(tx)][int(ty)]
                    if tile and tile != BEDROCK:
                        mining_effects.append(MiningEffect(int(tx), int(ty)))

        keys = pygame.key.get_pressed()

        # Horizontal accel/friction
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            vx -= accel * dt
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            vx += accel * dt
        else:
            # apply friction toward 0
            if vx > 0:
                vx = max(0.0, vx - friction * dt)
            elif vx < 0:
                vx = min(0.0, vx + friction * dt)

        vx = max(-max_speed, min(max_speed, vx))

        # Jump (use coyote time)
        if on_ground:
            coyote_left = coyote_time
        else:
            coyote_left = max(0.0, coyote_left - dt)

        want_jump = (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE])
        if want_jump and (on_ground or coyote_left > 0.0):
            vy = -jump_speed
            on_ground = False
            coyote_left = 0.0

        # Gravity
        vy = min(max_fall, vy + gravity * dt)

        # ---------------------- Move & collide: X axis -----------------------
        new_rect = player.copy()
        new_rect.x += int(round(vx * dt))

        x_start, x_end, y_start, y_end = tiles_overlapping_aabb(new_rect)
        if new_rect.x != player.x:
            step_right = new_rect.x > player.x
            collided = False
            for ty in range(y_start, y_end):
                # scan in movement direction for early exit
                tx_range = range(x_start, x_end)
                for tx in tx_range:
                    if not solid_at(world, tx, ty):
                        continue
                    tile_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if new_rect.colliderect(tile_rect):
                        collided = True
                        if step_right:
                            new_rect.right = tile_rect.left
                        else:
                            new_rect.left = tile_rect.right
                        vx = 0.0
                        break
                if collided:
                    break
        player.x = new_rect.x

        # ---------------------- Move & collide: Y axis -----------------------
        new_rect = player.copy()
        new_rect.y += int(round(vy * dt))

        x_start, x_end, y_start, y_end = tiles_overlapping_aabb(new_rect)
        was_falling = vy > 0
        on_ground = False
        if new_rect.y != player.y:
            step_down = new_rect.y > player.y
            collided = False
            for tx in range(x_start, x_end):
                for ty in range(y_start, y_end):
                    if not solid_at(world, tx, ty):
                        continue
                    tile_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if new_rect.colliderect(tile_rect):
                        collided = True
                        if step_down:
                            new_rect.bottom = tile_rect.top
                            on_ground = True
                        else:
                            new_rect.top = tile_rect.bottom
                        vy = 0.0
                        break
                if collided:
                    break
        player.y = new_rect.y

        # ------------------------------ Camera -------------------------------
        camera_x = max(0, min(player.centerx - SCREEN_WIDTH // 2, WORLD_WIDTH * TILE_SIZE - SCREEN_WIDTH))
        camera_y = max(0, min(player.centery - SCREEN_HEIGHT // 2, WORLD_HEIGHT * TILE_SIZE - SCREEN_HEIGHT))

        # ------------------------ Mining effects update ----------------------
        finished = []
        for eff in mining_effects:
            if eff.update():
                # Remove the tile when the effect finishes
                if 0 <= eff.x < WORLD_WIDTH and 0 <= eff.y < WORLD_HEIGHT:
                    world[eff.x][eff.y] = None
                finished.append(eff)
        for eff in finished:
            mining_effects.remove(eff)

        # -------------------------------- Draw -------------------------------
        screen.fill(SKY_BLUE)
        start_x = camera_x // TILE_SIZE
        end_x = (camera_x + SCREEN_WIDTH) // TILE_SIZE + 1
        start_y = camera_y // TILE_SIZE
        end_y = (camera_y + SCREEN_HEIGHT) // TILE_SIZE + 1

        for tx in range(start_x, end_x):
            for ty in range(start_y, end_y):
                if 0 <= tx < WORLD_WIDTH and 0 <= ty < WORLD_HEIGHT:
                    rect = pygame.Rect(tx * TILE_SIZE - camera_x, ty * TILE_SIZE - camera_y, TILE_SIZE, TILE_SIZE)
                    pygame.draw.rect(screen, BG_COLORS[world[tx][ty]] if world[tx][ty] else SKY_BLUE, rect)
                    tile = world[tx][ty]
                    if tile:
                        screen.blit(tile_surfaces[tile], rect.topleft)

        for eff in mining_effects:
            eff.draw(screen, camera_x, camera_y)

        pygame.draw.rect(
            screen, (255, 255, 0),
            pygame.Rect(player.x - camera_x, player.y - camera_y, player.width, player.height)
        )

        pygame.display.flip()

    pygame.quit()


if __name__ == '__main__':
    main()
