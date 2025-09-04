import math
import random
import pygame

# Configuration constants
TILE_SIZE = 32
WORLD_WIDTH = 100  # number of tiles horizontally
WORLD_HEIGHT = 100  # number of tiles vertically
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SKY_BLUE = (135, 206, 235)

# Tile type definitions
GRASS = 'grass'
DIRT = 'dirt'
STONE = 'stone'
GEM = 'gem'
BEDROCK = 'bedrock'

TILE_TYPES = [GRASS, DIRT, STONE, GEM, BEDROCK]

# Colors for tiles and backgrounds
TILE_COLORS = {
    GRASS: (34, 139, 34),
    DIRT: (139, 69, 19),
    STONE: (128, 128, 128),
    GEM: (128, 128, 128),  # base stone color, gem overlay drawn later
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


def create_tile_surface(base_color, detail_color=None):
    """Create a tile surface with small random detail."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    surf.fill(base_color)
    if detail_color is None:
        return surf
    for _ in range(20):
        x = random.randint(0, TILE_SIZE - 4)
        y = random.randint(0, TILE_SIZE - 4)
        w = random.randint(1, 3)
        h = random.randint(1, 3)
        rect = pygame.Rect(x, y, w, h)
        surf.fill(detail_color, rect)
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
        world[x][0] = GRASS
        background[x][0] = BG_COLORS[GRASS]
        dirt_depth = random.randint(9, 16)
        for y in range(1, dirt_depth):
            world[x][y] = DIRT
            background[x][y] = BG_COLORS[DIRT]
        for y in range(dirt_depth, WORLD_HEIGHT - 1):
            tile = STONE
            if random.random() < 0.05:
                tile = GEM
            world[x][y] = tile
            background[x][y] = BG_COLORS[tile]
        world[x][WORLD_HEIGHT - 1] = BEDROCK
        background[x][WORLD_HEIGHT - 1] = BG_COLORS[BEDROCK]
    return world, background


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

    player = pygame.Rect(5 * TILE_SIZE, -TILE_SIZE, TILE_SIZE // 2, TILE_SIZE)
    velocity = [0, 0]
    camera_x = 0
    mining_effects = []

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                tx = (mx + camera_x) // TILE_SIZE
                ty = (my + camera_y) // TILE_SIZE
                if 0 <= tx < WORLD_WIDTH and 0 <= ty < WORLD_HEIGHT:
                    tile = world[tx][ty]
                    if tile and tile != BEDROCK:
                        mining_effects.append(MiningEffect(tx, ty))

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            velocity[0] = -150
        elif keys[pygame.K_RIGHT]:
            velocity[0] = 150
        else:
            velocity[0] = 0
        if keys[pygame.K_SPACE] and velocity[1] == 0:
            velocity[1] = -300

        velocity[1] += 600 * dt
        player.x += int(velocity[0] * dt)
        player.y += int(velocity[1] * dt)

        # Collision
        for axis in (0, 1):
            if axis == 0:
                rect = player
            else:
                rect = player
            tiles_to_check = []
            x_start = rect.left // TILE_SIZE - 1
            x_end = rect.right // TILE_SIZE + 1
            y_start = rect.top // TILE_SIZE - 1
            y_end = rect.bottom // TILE_SIZE + 1
            for tx in range(x_start, x_end):
                for ty in range(y_start, y_end):
                    if 0 <= tx < WORLD_WIDTH and 0 <= ty < WORLD_HEIGHT:
                        if world[tx][ty]:
                            tiles_to_check.append(pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            for tile_rect in tiles_to_check:
                if rect.colliderect(tile_rect):
                    if axis == 0:
                        if velocity[0] > 0:
                            rect.right = tile_rect.left
                        elif velocity[0] < 0:
                            rect.left = tile_rect.right
                        velocity[0] = 0
                    else:
                        if velocity[1] > 0:
                            rect.bottom = tile_rect.top
                        elif velocity[1] < 0:
                            rect.top = tile_rect.bottom
                        velocity[1] = 0

        camera_x = max(0, min(player.centerx - SCREEN_WIDTH // 2, WORLD_WIDTH * TILE_SIZE - SCREEN_WIDTH))
        camera_y = max(0, min(player.centery - SCREEN_HEIGHT // 2, WORLD_HEIGHT * TILE_SIZE - SCREEN_HEIGHT))

        # Update mining effects
        finished = []
        for eff in mining_effects:
            if eff.update():
                world[eff.x][eff.y] = None
                finished.append(eff)
        for eff in finished:
            mining_effects.remove(eff)

        screen.fill(SKY_BLUE)
        # Draw background colors
        start_x = camera_x // TILE_SIZE
        end_x = (camera_x + SCREEN_WIDTH) // TILE_SIZE + 1
        start_y = camera_y // TILE_SIZE
        end_y = (camera_y + SCREEN_HEIGHT) // TILE_SIZE + 1
        for tx in range(start_x, end_x):
            for ty in range(start_y, end_y):
                if 0 <= tx < WORLD_WIDTH and 0 <= ty < WORLD_HEIGHT:
                    rect = pygame.Rect(tx * TILE_SIZE - camera_x, ty * TILE_SIZE - camera_y, TILE_SIZE, TILE_SIZE)
                    pygame.draw.rect(screen, background[tx][ty], rect)
                    tile = world[tx][ty]
                    if tile:
                        screen.blit(tile_surfaces[tile], rect.topleft)

        for eff in mining_effects:
            eff.draw(screen, camera_x, camera_y)

        pygame.draw.rect(screen, (255, 255, 0), pygame.Rect(player.x - camera_x, player.y - camera_y, player.width, player.height))

        pygame.display.flip()

    pygame.quit()


if __name__ == '__main__':
    main()
