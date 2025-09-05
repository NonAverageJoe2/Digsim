import math
import random
import pygame
import colorsys

# =============================================================================
# Platformer World (Pygame) + Ores Depth Progression + Teleport-to-Shop
# =============================================================================

# --------------------------------- Config -------------------------------------
TILE_SIZE = 32
WORLD_WIDTH = 100
WORLD_HEIGHT = 100
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SKY_BLUE = (135, 206, 235)
SURFACE_LEVEL = 10  # number of empty sky tiles above the ground surface

# Player size + bars
PLAYER_WIDTH_RATIO  = 0.42
PLAYER_HEIGHT_RATIO = 0.90

BAR_WIDTH  = TILE_SIZE
BAR_HEIGHT = 4
BAR_OFFSET = 1

HP_COLOR      = (210, 60, 60)
STAM_COLOR    = (70, 200, 110)
BAR_BG_COLOR  = (18, 18, 18)
BAR_BORDER    = (240, 240, 240)

# Mining range (tiles, Chebyshev distance)
MINING_RANGE_TILES = 2

# Tile types
GRASS   = 'grass'
DIRT    = 'dirt'
STONE   = 'stone'
COAL    = 'coal'
COPPER  = 'copper'
IRON    = 'iron'
GOLD    = 'gold'
EMERALD = 'emerald'
DIAMOND = 'diamond'
BEDROCK = 'bedrock'
TILE_TYPES = [GRASS, DIRT, STONE, COAL, COPPER, IRON, GOLD, EMERALD, DIAMOND, BEDROCK]

# Colors (base + background)
TILE_COLORS = {
    GRASS:   (34, 139, 34),
    DIRT:    (139, 69, 19),
    STONE:   (128, 128, 128),
    COAL:    (40, 40, 40),
    COPPER:  (184, 115, 51),
    IRON:    (190, 190, 190),
    GOLD:    (212, 175, 55),
    EMERALD: (46, 204, 113),
    DIAMOND: (0, 220, 220),
    BEDROCK: (10, 10, 10),
}
BG_COLORS = {
    GRASS:   (34, 139, 34),
    DIRT:    (101, 67, 33),
    STONE:   (70, 70, 70),
    COAL:    (55, 55, 55),
    COPPER:  (110, 80, 45),
    IRON:    (120, 120, 120),
    GOLD:    (85, 75, 40),
    EMERALD: (25, 80, 55),
    DIAMOND: (30, 70, 80),
    BEDROCK: (0, 0, 0),
}

# Mining durations (seconds, before tool & skill bonuses). jitter adds ±10%.
MINING_TIME = {
    GRASS:   0.25,
    DIRT:    0.50,
    STONE:   0.95,
    COAL:    0.90,
    COPPER:  1.00,
    IRON:    1.15,
    GOLD:    1.25,
    EMERALD: 1.40,
    DIAMOND: 1.60,
    BEDROCK: math.inf,
}
MINING_JITTER = 0.10

# Stamina
STAM_COST_PER_SEC = 20.0
STAM_MIN_COST     = 1.0
STAM_REGEN_MIN = 2.0
STAM_REGEN_MAX = 40.0
STAM_REGEN_EXP = 2.25
STAM_REGEN_DELAY = 3.0

# Health regen (like stamina, slower), delay after damage
HP_BASE_MAX = 100
HP_REGEN_MIN = 0.4
HP_REGEN_MAX = 6.0
HP_REGEN_EXP = 2.25
HP_REGEN_DELAY = 5.0

# Fog of war
FOG_RGBA = (30, 30, 30, 255)
FOG_BLOCKS_PLAYER = True

# Texture variety
VARIANTS_PER_TILE = {
    GRASS: 6, DIRT: 6, STONE: 6,
    COAL: 4, COPPER: 4, IRON: 4, GOLD: 4, EMERALD: 4, DIAMOND: 4,
    BEDROCK: 4
}
ALLOWED_FLIPS = {
    GRASS: (0, 1),
    DIRT: (0, 1),
    STONE: (0, 1, 2, 3),
    COAL: (0, 1, 2, 3),
    COPPER: (0, 1, 2, 3),
    IRON: (0, 1, 2, 3),
    GOLD: (0, 1, 2, 3),
    EMERALD: (0, 1, 2, 3),
    DIAMOND: (0, 1, 2, 3),
    BEDROCK: (0, 1, 2, 3),
}

# --- World GUI: Shop button (+ coins) ---
SHOP_BTN_RECT = pygame.Rect(10, 10, 110, 28)  # clickable
SHOP_UI_SURF = None
SHOP_FONT = None

# --- Hotbar / Inventory / Skills / Minimap UI ---
HOTBAR_SLOTS = 4
HOTBAR_H = 50
HOTBAR_PAD = 10
SLOT_SIZE = 40
SLOT_GAP = 8

INV_COLS = 6
INV_ROWS = 4
INV_CELL = 42
INV_PAD  = 12

SKILL_PANEL_W = 300
SKILL_PANEL_H = 150

MINIMAP_W = 180
MINIMAP_H = 180
MINIMAP_PAD = 10
MINIMAP_BG = (10, 10, 10, 220)

# Skills scaling
ENDURANCE_STAM_PER_LVL = 10            # +Max Stamina per level
ENDURANCE_DURA_REDUCT_PER_LVL = 0.005  # -0.5% durability loss per level
SPEED_MINING_BONUS_PER_LVL = 0.05      # +5% mining speed per level
INV_BASE_CAPACITY = 20
INV_PER_STRENGTH = 5
HP_PER_STRENGTH = 10

random.seed()
WORLD_SEED = random.randint(0, 2**31 - 1)

# ------------------------------ External Shop ---------------------------------
# Teleport into a separate scene; buying is only allowed in that scene.
try:
    from shop_scene import run_shop  # expected to manage prices and buying/selling
except Exception:
    run_shop = None
    print("[world] Note: shop_scene.run_shop not found. Shop button will warn when clicked.")

# --------------------------------- Items / Tools ------------------------------
ITEMS = {
    "hand":         {"type": "tool", "name": "Hand",          "color": (200, 200, 160)},
    "wood_pick":    {"type": "tool", "name": "Wood Pick",     "color": (160, 120, 60)},
    "stone_pick":   {"type": "tool", "name": "Stone Pick",    "color": (150, 150, 150)},
    "metal_pick":   {"type": "tool", "name": "Metal Pick",    "color": (180, 180, 210)},
    "wood_shovel":  {"type": "tool", "name": "Wood Shovel",   "color": (170, 130, 70)},
    "metal_shovel": {"type": "tool", "name": "Metal Shovel",  "color": (190, 190, 215)},
    "sword":        {"type": "tool", "name": "Sword",         "color": (210, 210, 230)},

    "hp_potion":    {"type": "consumable", "name": "HP Potion",   "color": (210, 60, 60)},
    "stam_potion":  {"type": "consumable", "name": "Stam Potion", "color": (70, 200, 110)},

    "grass_item":   {"type": "res",  "name": "Grass",         "color": TILE_COLORS[GRASS]},
    "dirt_item":    {"type": "res",  "name": "Dirt",          "color": TILE_COLORS[DIRT]},
    "stone_item":   {"type": "res",  "name": "Stone",         "color": TILE_COLORS[STONE]},

    "coal_item":    {"type": "res",  "name": "Coal",          "color": TILE_COLORS[COAL]},
    "copper_item":  {"type": "res",  "name": "Copper",        "color": TILE_COLORS[COPPER]},
    "iron_item":    {"type": "res",  "name": "Iron",          "color": TILE_COLORS[IRON]},
    "gold_item":    {"type": "res",  "name": "Gold",          "color": TILE_COLORS[GOLD]},
    "emerald_item": {"type": "res",  "name": "Emerald",       "color": TILE_COLORS[EMERALD]},
    "diamond_item": {"type": "res",  "name": "Diamond",       "color": TILE_COLORS[DIAMOND]},
}

# Tool mining speed factor (duration is divided by this)
TOOL_SPEED = {
    "hand":        {GRASS: 1.0, DIRT: 1.0, STONE: 0.6, COAL: 0.7, COPPER: 0.65, IRON: 0.55, GOLD: 0.50, EMERALD: 0.45, DIAMOND: 0.40},
    "wood_pick":   {GRASS: 1.1, DIRT: 1.2, STONE: 1.3, COAL: 1.35, COPPER: 1.25, IRON: 1.10, GOLD: 1.05, EMERALD: 0.9,  DIAMOND: 0.8},
    "stone_pick":  {GRASS: 1.2, DIRT: 1.35,STONE: 1.55,COAL: 1.6,  COPPER: 1.45, IRON: 1.35, GOLD: 1.2,  EMERALD: 1.05, DIAMOND: 0.95},
    "metal_pick":  {GRASS: 1.3, DIRT: 1.6, STONE: 2.1, COAL: 2.2,  COPPER: 2.0,  IRON: 1.9,  GOLD: 1.8,  EMERALD: 1.6,  DIAMOND: 1.45},
    "wood_shovel": {GRASS: 1.6, DIRT: 1.5, STONE: 0.6, COAL: 0.6,  COPPER: 0.55, IRON: 0.5,  GOLD: 0.5,  EMERALD: 0.45, DIAMOND: 0.4},
    "metal_shovel":{GRASS: 2.0, DIRT: 1.8, STONE: 0.8, COAL: 0.85, COPPER: 0.8,  IRON: 0.75, GOLD: 0.7,  EMERALD: 0.65, DIAMOND: 0.6},
    "sword":       {GRASS: 1.0, DIRT: 0.8, STONE: 0.5, COAL: 0.5,  COPPER: 0.5,  IRON: 0.45, GOLD: 0.45, EMERALD: 0.4,  DIAMOND: 0.35},
}

# Tool durability (None => infinite, e.g., Hand)
TOOL_MAX_DUR = {
    "hand":        None,
    "wood_pick":   100,
    "stone_pick":  160,
    "metal_pick":  280,
    "wood_shovel": 100,
    "metal_shovel":240,
    "sword":       250,
}
# Durability loss per mined block by tile
TOOL_DECAY_PER_BLOCK = {
    GRASS: 0.5, DIRT: 1.0, STONE: 1.5,
    COAL: 1.2, COPPER: 1.3, IRON: 1.6,
    GOLD: 1.6, EMERALD: 1.8, DIAMOND: 2.2
}

# --------------------------------- Helpers ------------------------------------
def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v

def create_base_surf(color):
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    surf.fill(color)
    return surf

def add_speckles(surf, count, color_range, size_range=(1, 2), margin=0):
    w, h = surf.get_size()
    for _ in range(count):
        x = random.randint(margin, w - 1 - margin)
        y = random.randint(margin, h - 1 - margin)
        rw = random.randint(size_range[0], size_range[1])
        rh = random.randint(size_range[0], size_range[1])
        c = (
            random.randint(color_range[0][0], color_range[1][0]),
            random.randint(color_range[0][1], color_range[1][1]),
            random.randint(color_range[0][2], color_range[1][2]),
        )
        pygame.draw.rect(surf, c, pygame.Rect(x, y, rw, rh))

def add_crack(surf, segments, color, thickness=1):
    w, h = surf.get_size()
    x = random.randint(2, w-3)
    y = random.randint(2, h-3)
    pts = [(x, y)]
    for _ in range(segments):
        x += random.randint(-4, 4)
        y += random.randint(-3, 3)
        x = clamp(x, 1, w-2)
        y = clamp(y, 1, h-2)
        pts.append((x, y))
    if len(pts) >= 2:
        pygame.draw.lines(surf, color, False, pts, thickness)

def tint_slight(surf, dr, dg, db, a=36):
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    overlay.fill((max(0,dr), max(0,dg), max(0,db), a))
    surf.blit(overlay, (0,0), special_flags=pygame.BLEND_RGBA_ADD)

def top_gradient(surf, color_light, height=5):
    for y in range(height):
        t = (height - y) / height
        line = pygame.Surface((TILE_SIZE, 1), pygame.SRCALPHA)
        line.fill((*color_light, int(36 * t)))
        surf.blit(line, (0, y))

def dirt_strata(surf, bands=2):
    for _ in range(bands):
        y = random.randint(8, 18)
        c = (120 + random.randint(-5,5), 68 + random.randint(-5,5), 28 + random.randint(-5,5))
        pygame.draw.line(surf, c, (0, y), (TILE_SIZE, y), 1)

def add_grass_tufts(surf, rows=2):
    for _ in range(random.randint(3, 5)):
        x = random.randint(2, TILE_SIZE - 3)
        h = random.randint(3, 4 + rows)
        for i in range(h):
            col = (52 + i*2, 180, 64 + i*2)
            surf.set_at((x, 1+i), col)
            if random.random() < 0.45 and x+1 < TILE_SIZE:
                surf.set_at((x+1, 1+i), col)

def add_ore_overlay(surf, color, outline=(255,255,255), count=(1,2), max_r=4):
    """Generic ore blob overlay."""
    w, h = surf.get_size()
    for _ in range(random.randint(count[0], count[1])):
        cx = random.randint(6, w-6)
        cy = random.randint(6, h-6)
        r  = random.randint(3, max_r)
        pygame.draw.circle(surf, color, (cx, cy), r)
        pygame.draw.circle(surf, outline, (cx, cy), r, 1)

def build_flips_for_variant(s: pygame.Surface, tile_type: str):
    flips = []
    for code in ALLOWED_FLIPS[tile_type]:
        if code == 0: flips.append(s)
        elif code == 1: flips.append(pygame.transform.flip(s, True, False))
        elif code == 2: flips.append(pygame.transform.flip(s, False, True))
        else: flips.append(pygame.transform.flip(s, True, True))
    return flips

def build_tile_variants():
    tile_variants = {t: [] for t in TILE_TYPES}

    # Grass
    for _ in range(VARIANTS_PER_TILE[GRASS]):
        s = create_base_surf(TILE_COLORS[GRASS])
        top_gradient(s, (80, 220, 90), height=5)
        add_grass_tufts(s, rows=random.randint(1,3))
        add_speckles(s, random.randint(6,10), ((20,120,20), (40,150,40)), (1,2), 1)
        tint_slight(s, random.randint(-4,4), random.randint(-4,4), random.randint(-4,4), a=28)
        tile_variants[GRASS].append(build_flips_for_variant(s, GRASS))

    # Dirt
    for _ in range(VARIANTS_PER_TILE[DIRT]):
        s = create_base_surf(TILE_COLORS[DIRT])
        top_gradient(s, (180, 110, 50), height=3)
        dirt_strata(s, bands=random.randint(1,2))
        add_speckles(s, random.randint(12,18), ((95,55,20), (150,95,48)), (1,2), 1)
        tint_slight(s, random.randint(-6,4), random.randint(-6,4), random.randint(-6,4), a=30)
        tile_variants[DIRT].append(build_flips_for_variant(s, DIRT))

    # Stone
    for _ in range(VARIANTS_PER_TILE[STONE]):
        s = create_base_surf(TILE_COLORS[STONE])
        add_speckles(s, random.randint(8,12), ((100,100,100),(118,118,118)), (1,2), 1)
        for _ in range(random.randint(1,2)):
            add_crack(s, random.randint(3,5), (80,80,80), 1)
        tint_slight(s, random.randint(-4,4), random.randint(-4,4), random.randint(-4,4), a=24)
        tile_variants[STONE].append(build_flips_for_variant(s, STONE))

    # Ores
    def ore_variant(base_color, ore_color, tile_type, speckles=((100,100,100),(120,120,120))):
        s = create_base_surf(base_color)
        add_speckles(s, random.randint(6,9), speckles, (1,2), 1)
        add_ore_overlay(s, ore_color)
        tile_variants[tile_type].append(build_flips_for_variant(s, tile_type))

    for _ in range(VARIANTS_PER_TILE[COAL]):
        ore_variant(TILE_COLORS[STONE], (35,35,35), COAL)
    for _ in range(VARIANTS_PER_TILE[COPPER]):
        ore_variant(TILE_COLORS[STONE], (200,140,70), COPPER)
    for _ in range(VARIANTS_PER_TILE[IRON]):
        ore_variant(TILE_COLORS[STONE], (210,210,210), IRON)
    for _ in range(VARIANTS_PER_TILE[GOLD]):
        ore_variant(TILE_COLORS[STONE], (230, 190, 60), GOLD)
    for _ in range(VARIANTS_PER_TILE[EMERALD]):
        ore_variant(TILE_COLORS[STONE], (46, 204, 113), EMERALD)
    for _ in range(VARIANTS_PER_TILE[DIAMOND]):
        ore_variant(TILE_COLORS[STONE], (0, 240, 240), DIAMOND)

    # Bedrock
    for _ in range(VARIANTS_PER_TILE[BEDROCK]):
        s = create_base_surf(TILE_COLORS[BEDROCK])
        for _ in range(random.randint(1,2)):
            add_crack(s, random.randint(4,6), (5,5,5), 2)
        add_speckles(s, random.randint(6,9), ((12,12,12),(24,24,24)), (1,2), 1)
        tile_variants[BEDROCK].append(build_flips_for_variant(s, BEDROCK))

    return tile_variants

def prng_int(x, y, salt):
    n = (x * 73856093) ^ (y * 19349663) ^ (WORLD_SEED * 83492791) ^ (salt * 2654435761)
    n ^= (n >> 13)
    n = (n * 1274126177) & 0xFFFFFFFF
    n ^= (n >> 16)
    return n & 0xFFFFFFFF

SALT_BY_TILE = {
    GRASS:101, DIRT:202, STONE:303, COAL:311, COPPER:322, IRON:333,
    GOLD:344, EMERALD:355, DIAMOND:366, BEDROCK:505
}

def pick_variant_surface(tile_type, tx, ty, variants_dict):
    var_list = variants_dict[tile_type]
    if not var_list:
        return None
    r = prng_int(tx, ty, SALT_BY_TILE[tile_type])
    v_idx = r % len(var_list)
    flips = var_list[v_idx]
    f_idx = (r >> 3) % len(flips)
    return flips[f_idx]

def smooth_dirt_depths(width: int, min_depth: int, max_depth: int) -> list[int]:
    start = random.randint((min_depth + max_depth)//2 - 1, (min_depth + max_depth)//2 + 1)
    d = [start]
    for _ in range(1, width):
        r = random.random()
        step = -1 if r < 0.18 else (1 if r > 0.82 else 0)
        d.append(max(min_depth, min(max_depth, d[-1] + step)))
    smoothed = []
    for x in range(width):
        acc = d[x]; cnt = 1
        if x > 0: acc += d[x-1]; cnt += 1
        if x < width-1: acc += d[x+1]; cnt += 1
        smoothed.append(int(round(acc / cnt)))
    return smoothed

def generate_world():
    """
    Generate terrain with smoothed dirt thickness and ores by depth:
      Shallow → deep rarity: Coal > Copper > Iron > Gold > Emerald > Diamond.
    """
    world = [[None for _ in range(WORLD_HEIGHT)] for _ in range(WORLD_WIDTH)]
    background = [[SKY_BLUE for _ in range(WORLD_HEIGHT)] for _ in range(WORLD_WIDTH)]
    dirt_depth_by_x = smooth_dirt_depths(WORLD_WIDTH, 9, 16)

    for x in range(WORLD_WIDTH):
        ground_y = SURFACE_LEVEL
        world[x][ground_y] = GRASS
        background[x][ground_y] = BG_COLORS[GRASS]

        dirt_depth = dirt_depth_by_x[x]
        # Dirt below grass
        for y in range(ground_y + 1, min(WORLD_HEIGHT - 1, ground_y + dirt_depth)):
            world[x][y] = DIRT
            background[x][y] = BG_COLORS[DIRT]

        # Stone + Ores
        for y in range(ground_y + dirt_depth, WORLD_HEIGHT - 1):
            # Depth normalized 0..1 from start of stone down to bedrock
            stone_start = ground_y + dirt_depth
            stone_h = (WORLD_HEIGHT - 1) - stone_start
            dnorm = 0.0 if stone_h <= 0 else (y - stone_start) / stone_h

            # Base stone
            tile = STONE

            # Depth-biased ore probabilities
            r = random.random()
            # Coal: shallow (dnorm < ~0.35), decent chance
            if dnorm < 0.35 and r < 0.08:
                tile = COAL
            # Copper: shallow-mid
            elif dnorm < 0.50 and r < 0.06:
                tile = COPPER
            # Iron: mid
            elif 0.30 < dnorm < 0.75 and r < 0.05:
                tile = IRON
            # Gold: deeper
            elif dnorm > 0.55 and r < 0.035:
                tile = GOLD
            # Emerald: deep
            elif dnorm > 0.70 and r < 0.025:
                tile = EMERALD
            # Diamond: deepest
            elif dnorm > 0.82 and r < 0.015:
                tile = DIAMOND

            world[x][y] = tile
            background[x][y] = BG_COLORS[tile if tile != STONE else STONE]

        # Bedrock bottom
        world[x][WORLD_HEIGHT - 1] = BEDROCK
        background[x][WORLD_HEIGHT - 1] = BG_COLORS[BEDROCK]

    return world, background

def init_revealed(world):
    revealed = [[False for _ in range(WORLD_HEIGHT)] for _ in range(WORLD_WIDTH)]
    for x in range(WORLD_WIDTH):
        for y in range(0, SURFACE_LEVEL):
            revealed[x][y] = True
        if world[x][SURFACE_LEVEL] == GRASS:
            revealed[x][SURFACE_LEVEL] = True
    return revealed

def reveal_tile(revealed, x, y):
    if 0 <= x < WORLD_WIDTH and 0 <= y < WORLD_HEIGHT:
        revealed[x][y] = True

def reveal_neighbors4(revealed, x, y):
    reveal_tile(revealed, x + 1, y)
    reveal_tile(revealed, x - 1, y)
    reveal_tile(revealed, x, y + 1)
    reveal_tile(revealed, x, y - 1)

def solid_at(world, tx, ty):
    if 0 <= tx < WORLD_WIDTH and 0 <= ty < WORLD_HEIGHT:
        return world[tx][ty] is not None
    return True

def tiles_overlapping_aabb(rect):
    x_start = max(0, rect.left // TILE_SIZE - 1)
    x_end = min(WORLD_WIDTH, rect.right // TILE_SIZE + 2)
    y_start = max(0, rect.top // TILE_SIZE - 1)
    y_end = min(WORLD_HEIGHT, rect.bottom // TILE_SIZE + 2)
    return x_start, x_end, y_start, y_end

def mining_time_for(tile_type: str) -> float:
    base = MINING_TIME.get(tile_type, 0.6)
    if base == math.inf:
        return math.inf
    jitter = 1.0 + random.uniform(-MINING_JITTER, MINING_JITTER)
    return max(0.05, base * jitter)

def stamina_cost_for_duration(duration_s: float) -> int:
    if not math.isfinite(duration_s):
        return 999999
    cost = max(STAM_MIN_COST, duration_s * STAM_COST_PER_SEC)
    return int(round(cost))

def color_for_tile(tile_type: str) -> tuple[int, int, int]:
    if tile_type == GRASS:   h = 0.30
    elif tile_type == DIRT:  h = 0.08
    elif tile_type == COAL:  h = 0.02
    elif tile_type == COPPER:h = 0.06
    elif tile_type == IRON:  h = 0.00
    elif tile_type == GOLD:  h = 0.13
    elif tile_type == EMERALD:h= 0.35
    elif tile_type == DIAMOND:h= 0.55
    else:                    h = 0.60
    s = 0.35; v = 1.0
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r*255), int(g*255), int(b*255))

def stamina_regen_rate(current: float, max_value: float) -> float:
    if max_value <= 0: return 0.0
    s = max(0.0, min(1.0, current / max_value))
    return STAM_REGEN_MIN + STAM_REGEN_MAX * (s ** STAM_REGEN_EXP)

def health_regen_rate(current: float, max_value: float) -> float:
    if max_value <= 0: return 0.0
    s = max(0.0, min(1.0, current / max_value))
    return HP_REGEN_MIN + HP_REGEN_MAX * (s ** HP_REGEN_EXP)

def can_mine_tile(player_rect: pygame.Rect, tx: int, ty: int, radius_tiles: int) -> bool:
    pcx = player_rect.centerx // TILE_SIZE
    pcy = player_rect.centery // TILE_SIZE
    dx = abs(int(tx) - int(pcx))
    dy = abs(int(ty) - int(pcy))
    return max(dx, dy) <= radius_tiles

# ---- Surface spawn helpers (GLOBAL) ------------------------------------------
def _top_solid_pixel_y(world, tx: int) -> int:
    tx = max(0, min(WORLD_WIDTH - 1, int(tx)))
    for y in range(WORLD_HEIGHT):
        if world[tx][y] is not None:
            return y * TILE_SIZE
    return SURFACE_LEVEL * TILE_SIZE

def spawn_player_on_surface(world, player: pygame.Rect, prefer_tx: int | None = None) -> None:
    if prefer_tx is None:
        prefer_tx = player.centerx // TILE_SIZE
    prefer_tx = max(0, min(WORLD_WIDTH - 1, int(prefer_tx)))
    top_y = _top_solid_pixel_y(world, prefer_tx)
    center_x_px = prefer_tx * TILE_SIZE + TILE_SIZE // 2
    # Correct: bottom sits at top_y, not inside
    player.midbottom = (center_x_px, top_y)


# ------------- Unstick helpers (safe after teleport) --------------------------
def push_player_out_of_solids(world, rect: pygame.Rect) -> pygame.Rect:
    x_start, x_end, y_start, y_end = tiles_overlapping_aabb(rect)
    for ty in range(y_start, y_end):
        for tx in range(x_start, x_end):
            if not solid_at(world, tx, ty):
                continue
            tile_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if rect.colliderect(tile_rect):
                ox1 = tile_rect.right - rect.left
                ox2 = rect.right - tile_rect.left
                oy1 = tile_rect.bottom - rect.top
                oy2 = rect.bottom - tile_rect.top
                moves = [(ox1, 0), (-ox2, 0), (0, oy1), (0, -oy2)]
                dx, dy = min(moves, key=lambda v: abs(v[0]) + abs(v[1]))
                rect.move_ip(dx, dy)
                return push_player_out_of_solids(world, rect)
    return rect

def snap_player_to_ground(world, rect: pygame.Rect, max_fall_px: int = TILE_SIZE * 4) -> tuple[pygame.Rect, bool]:
    on_ground = False
    fall = 0
    while fall < max_fall_px:
        test = rect.move(0, 1)
        x_start, x_end, y_start, y_end = tiles_overlapping_aabb(test)
        hit = False
        for ty in range(y_start, y_end):
            for tx in range(x_start, x_end):
                if not solid_at(world, tx, ty):
                    continue
                tile_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if test.colliderect(tile_rect):
                    hit = True
                    on_ground = True
                    break
            if hit:
                break
        if hit:
            break
        rect = test
        fall += 1
    return rect, on_ground

# ------------------------------ Effects ---------------------------------------
class MiningEffect:
    DEG_SEQUENCE = [90, 135, 45, 0, 180, 225, 315, 270, 112.5, 67.5, 22.5, -22.5, -67.5, -112.5, -157.5, 157.5]
    def __init__(self, x: int, y: int, duration_s: float, tile_type: str):
        self.x = int(x); self.y = int(y)
        self.t = 0.0
        self.duration = max(0.01, float(duration_s))
        self.color = color_for_tile(tile_type)
        self.angles = [math.radians(d) for d in self.DEG_SEQUENCE]
        self.dirs = [(math.cos(a), math.sin(a)) for a in self.angles]
        self.phases = len(self.dirs)
    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t >= self.duration
    def _draw_pretty_line(self, fx_surf, cx, cy, ex, ey):
        pygame.draw.line(fx_surf, (*self.color, 70), (cx, cy), (ex, ey), 6)
        pygame.draw.line(fx_surf, (*self.color, 150), (cx, cy), (ex, ey), 3)
        pygame.draw.aaline(fx_surf, (255,255,255,255), (cx, cy), (ex, ey))
    def draw(self, surface, camera_x, camera_y):
        cx = self.x * TILE_SIZE - camera_x + TILE_SIZE // 2
        cy = self.y * TILE_SIZE - camera_y + TILE_SIZE // 2
        p = max(0.0, min(0.9999, self.t / self.duration))
        f = p * self.phases
        phase_idx = int(f)
        phase_frac = f - phase_idx
        fx = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        lc = TILE_SIZE * 0.44
        for i in range(0, phase_idx):
            dx, dy = self.dirs[i]
            ex = TILE_SIZE // 2 + dx * lc
            ey = TILE_SIZE // 2 - dy * lc
            self._draw_pretty_line(fx, TILE_SIZE // 2, TILE_SIZE // 2, ex, ey)
        if phase_idx < self.phases:
            dx, dy = self.dirs[phase_idx]
            length = lc * (0.2 + 0.8 * phase_frac)
            ex = TILE_SIZE // 2 + dx * length
            ey = TILE_SIZE // 2 - dy * length
            self._draw_pretty_line(fx, TILE_SIZE // 2, TILE_SIZE // 2, ex, ey)
        surface.blit(fx, (cx - TILE_SIZE // 2, cy - TILE_SIZE // 2))

# --------------------------- UI: Bars above player ----------------------------
def draw_player_bars(screen: pygame.Surface, cam_x: int, cam_y: int,
                     player: pygame.Rect, hp: float, hp_max: int,
                     stam: float, stam_max: int) -> None:
    px = player.centerx - cam_x
    py_top = player.top - cam_y
    x = int(px - BAR_WIDTH // 2)
    y_top = int(py_top - BAR_OFFSET - (BAR_HEIGHT * 2))
    if x > SCREEN_WIDTH or x + BAR_WIDTH < 0 or y_top > SCREEN_HEIGHT or y_top + BAR_HEIGHT * 2 < 0:
        return
    def draw_bar(x, y, value, max_value, fill_color):
        v = 0 if max_value <= 0 else max(0.0, min(1.0, value / max_value))
        pygame.draw.rect(screen, BAR_BG_COLOR, pygame.Rect(x, y, BAR_WIDTH, BAR_HEIGHT))
        fill_w = max(0, int(BAR_WIDTH * v))
        if fill_w > 0:
            pygame.draw.rect(screen, fill_color, pygame.Rect(x, y, fill_w, BAR_HEIGHT))
        pygame.draw.rect(screen, BAR_BORDER, pygame.Rect(x, y, BAR_WIDTH, BAR_HEIGHT), 1)
    draw_bar(x, y_top, hp, hp_max, HP_COLOR)
    draw_bar(x, y_top + BAR_HEIGHT, stam, stam_max, STAM_COLOR)

# ------------------------ GUI cache: Shop button (draw once) ------------------
def build_shop_button_ui(screen):
    global SHOP_UI_SURF, SHOP_FONT
    sw, sh = screen.get_size()
    if SHOP_UI_SURF is not None and SHOP_UI_SURF.get_size() == (sw, sh):
        return
    SHOP_UI_SURF = pygame.Surface((sw, sh), pygame.SRCALPHA)
    SHOP_FONT = pygame.font.SysFont(None, 22)
    pygame.draw.rect(SHOP_UI_SURF, (30, 30, 30), SHOP_BTN_RECT, border_radius=6)
    label = SHOP_FONT.render("Shop", True, (235, 235, 235))
    SHOP_UI_SURF.blit(label, (SHOP_BTN_RECT.x + 12, SHOP_BTN_RECT.y + 6))

# ------------------------------ Inventory / Skills ----------------------------
def total_items(inv: dict[str, int]) -> int:
    return sum(inv.values())

def capacity_for_strength(strength_lvl: int) -> int:
    return INV_BASE_CAPACITY + strength_lvl * INV_PER_STRENGTH

def hp_for_strength(strength_lvl: int) -> int:
    return HP_BASE_MAX + strength_lvl * HP_PER_STRENGTH

def stam_for_endurance(endurance_lvl: int) -> int:
    return 100 + endurance_lvl * ENDURANCE_STAM_PER_LVL

def current_tool_factor(tool_id: str, tile_type: str) -> float:
    d = TOOL_SPEED.get(tool_id, {})
    return max(0.1, d.get(tile_type, 1.0))

def draw_item_icon(surf: pygame.Surface, rect: pygame.Rect, item_id: str):
    info = ITEMS.get(item_id)
    if not info: return
    pygame.draw.rect(surf, info["color"], rect.inflate(-8, -8), border_radius=6)

def draw_hotbar(screen: pygame.Surface, font: pygame.font.Font,
                slots: list[str | None], selected_idx: int):
    sw, sh = screen.get_size()
    total_w = HOTBAR_SLOTS * SLOT_SIZE + (HOTBAR_SLOTS - 1) * SLOT_GAP
    x0 = (sw - total_w) // 2
    y0 = sh - HOTBAR_H
    strip = pygame.Rect(x0 - HOTBAR_PAD, y0 - HOTBAR_PAD, total_w + HOTBAR_PAD*2, SLOT_SIZE + HOTBAR_PAD*2)
    pygame.draw.rect(screen, (20, 20, 20), strip, border_radius=12)
    pygame.draw.rect(screen, (90, 90, 90), strip, 1, border_radius=12)
    for i in range(HOTBAR_SLOTS):
        r = pygame.Rect(x0 + i*(SLOT_SIZE + SLOT_GAP), y0, SLOT_SIZE, SLOT_SIZE)
        pygame.draw.rect(screen, (35,35,35), r, border_radius=8)
        if i == selected_idx:
            pygame.draw.rect(screen, (230, 230, 120), r, 2, border_radius=8)
        else:
            pygame.draw.rect(screen, (120, 120, 120), r, 1, border_radius=8)
        item = slots[i]
        if item:
            draw_item_icon(screen, r, item)
        num = font.render(str(i+1), True, (220,220,220))
        screen.blit(num, (r.x + 4, r.y + 2))

def draw_inventory(screen: pygame.Surface, font: pygame.font.Font,
                   inv: dict[str,int], tools_owned: dict[str, float],
                   selected_hotbar_slot: int, open_panel: bool,
                   strength_lvl: int):
    sw, sh = screen.get_size()
    if not open_panel:
        return [], []  # (item_cells, tool_cells)

    panel_w = INV_PAD*2 + INV_COLS*INV_CELL + (INV_COLS-1)*6
    panel_h = INV_PAD*2 + INV_ROWS*INV_CELL + (INV_ROWS-1)*6 + 54
    panel = pygame.Rect(10, sh - HOTBAR_H - 56 - panel_h - 8, panel_w, panel_h)
    pygame.draw.rect(screen, (18,18,18), panel, border_radius=10)
    pygame.draw.rect(screen, (120,120,120), panel, 1, border_radius=10)

    title = font.render(f"Inventory  {total_items(inv)}/{capacity_for_strength(strength_lvl)}", True, (235,235,235))
    screen.blit(title, (panel.x + 12, panel.y + 8))

    # Tools row
    tool_text = font.render("Tools:", True, (220,220,220))
    screen.blit(tool_text, (panel.x + 12, panel.y + 28))
    tool_cells = []
    tx = panel.x + 70
    ty = panel.y + 24
    for tool_id, dur in tools_owned.items():
        if tool_id == "hand":  # skip, always available
            continue
        cell = pygame.Rect(tx, ty, 30, 30)
        pygame.draw.rect(screen, (35,35,35), cell, border_radius=6)
        pygame.draw.rect(screen, (80,80,80), cell, 1, border_radius=6)
        draw_item_icon(screen, cell, tool_id)
        # durability bar
        mx = TOOL_MAX_DUR.get(tool_id)
        if mx and mx > 0:
            v = max(0.0, min(1.0, (dur or 0)/mx))
            bar = pygame.Rect(cell.x, cell.bottom+2, 30, 4)
            pygame.draw.rect(screen, (40,40,40), bar)
            pygame.draw.rect(screen, (200,200,90), (bar.x, bar.y, int(30*v), 4))
        name = ITEMS[tool_id]["name"]
        nm = font.render(name, True, (200,200,200))
        screen.blit(nm, (cell.x - 4, cell.bottom + 8))
        tool_cells.append((cell, tool_id))
        tx += 36

    # Items grid (resources/potions)
    clickable_cells = []
    y = panel.y + 72
    idx = 0
    for r in range(INV_ROWS):
        x = panel.x + INV_PAD
        for c in range(INV_COLS):
            cell = pygame.Rect(x, y, INV_CELL, INV_CELL)
            pygame.draw.rect(screen, (30,30,30), cell, border_radius=8)
            pygame.draw.rect(screen, (80,80,80), cell, 1, border_radius=8)
            if idx < len(inv):
                item_id = list(inv.keys())[idx]
                draw_item_icon(screen, cell, item_id)
                cnt = inv[item_id]
                cnt_txt = font.render(str(cnt), True, (240,240,240))
                screen.blit(cnt_txt, (cell.right - cnt_txt.get_width() - 6, cell.bottom - cnt_txt.get_height() - 4))
                clickable_cells.append((cell, item_id))
            x += INV_CELL + 6
            idx += 1
        y += INV_CELL + 6

    help_txt = font.render(f"Click a tool to equip to slot {selected_hotbar_slot+1}", True, (200,200,200))
    screen.blit(help_txt, (panel.x + 12, panel.bottom - 22))
    return clickable_cells, tool_cells

def draw_skills(screen: pygame.Surface, font: pygame.font.Font,
                open_panel: bool, strength_lvl: int, endurance_lvl: int,
                speed_lvl: int, skill_points: int):
    if not open_panel:
        return {}

    panel = pygame.Rect(200, SCREEN_HEIGHT - HOTBAR_H - 56 - SKILL_PANEL_H - 8, SKILL_PANEL_W, SKILL_PANEL_H)
    pygame.draw.rect(screen, (18,18,18), panel, border_radius=10)
    pygame.draw.rect(screen, (120,120,120), panel, 1, border_radius=10)
    title = font.render(f"Skills   Points: {skill_points}", True, (235,235,235))
    screen.blit(title, (panel.x + 12, panel.y + 8))

    clickable = {}

    def row(y, label, lvl, explain):
        txt = font.render(f"{label}  Lv {lvl}  {explain}", True, (220,220,220))
        screen.blit(txt, (panel.x + 12, y))
        plus = pygame.Rect(panel.right - 34, y - 4, 24, 24)
        pygame.draw.rect(screen, (40,40,40), plus, border_radius=6)
        pygame.draw.rect(screen, (200,200,200), plus, 1, border_radius=6)
        ptxt = font.render("+", True, (230,230,230))
        screen.blit(ptxt, (plus.centerx - ptxt.get_width()/2, plus.centery - ptxt.get_height()/2))
        return plus

    y0 = panel.y + 40
    clickable["str"] = row(y0, "Strength", strength_lvl,
                           f"(HP {hp_for_strength(strength_lvl)}, Cap {capacity_for_strength(strength_lvl)})")
    clickable["end"] = row(y0+36, "Endurance", endurance_lvl,
                           f"(Stam {stam_for_endurance(endurance_lvl)}, Dur -{int(ENDURANCE_DURA_REDUCT_PER_LVL*1000)/10}%/lvl)")
    clickable["spd"] = row(y0+72, "Speed", speed_lvl,
                           f"(Mining +{int(SPEED_MINING_BONUS_PER_LVL*100)}%/lvl)")
    return clickable

# ------------------------------ Minimap ---------------------------------------
def build_minimap(world, revealed):
    surf = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT)).convert()
    px = pygame.PixelArray(surf)
    for x in range(WORLD_WIDTH):
        for y in range(WORLD_HEIGHT):
            if y < SURFACE_LEVEL:
                px[x, y] = 0xFFFFFF
            else:
                if not revealed[x][y]:
                    px[x, y] = 0x000000
                else:
                    if world[x][y] is None:
                        px[x, y] = (120 << 16) | (120 << 8) | 120
                    else:
                        px[x, y] = 0xFFFFFF
    del px
    return surf

def draw_minimap_small(screen: pygame.Surface, mini: pygame.Surface):
    sw, sh = screen.get_size()
    target = pygame.transform.smoothscale(mini, (MINIMAP_W, MINIMAP_H))
    bg = pygame.Surface((MINIMAP_W + 8, MINIMAP_H + 8), pygame.SRCALPHA)
    bg.fill(MINIMAP_BG)
    x = sw - MINIMAP_W - MINIMAP_PAD
    y = MINIMAP_PAD
    screen.blit(bg, (x - 4, y - 4))
    screen.blit(target, (x, y))
    return pygame.Rect(x, y, MINIMAP_W, MINIMAP_H)

def draw_minimap_big(screen: pygame.Surface, mini: pygame.Surface):
    sw, sh = screen.get_size()
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0,0,0,180))
    screen.blit(overlay, (0,0))
    scale = min((sw - 80) / WORLD_WIDTH, (sh - 120) / WORLD_HEIGHT)
    tw, th = int(WORLD_WIDTH * scale), int(WORLD_HEIGHT * scale)
    target = pygame.transform.smoothscale(mini, (tw, th))
    screen.blit(target, ((sw - tw)//2, (sh - th)//2))
    font = pygame.font.SysFont(None, 24)
    t = font.render("Minimap (M to close)", True, (240,240,240))
    screen.blit(t, (sw//2 - t.get_width()//2, 24))

# ---------------------------------- Main --------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    build_shop_button_ui(screen)

    font = pygame.font.SysFont(None, 20)
    big_font = pygame.font.SysFont(None, 24)

    tile_variants = build_tile_variants()
    world, background = generate_world()
    revealed = init_revealed(world)

    fog_tile = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    fog_tile.fill(FOG_RGBA)

    # Player (spawn on surface at column 5)
    player = pygame.Rect(
        5 * TILE_SIZE, 0,
        int(TILE_SIZE * PLAYER_WIDTH_RATIO),
        int(TILE_SIZE * PLAYER_HEIGHT_RATIO),
    )
    spawn_player_on_surface(world, player, 5)
    vx, vy = 0.0, 0.0
    accel = 900.0
    max_speed = 180.0
    friction = 1200.0
    gravity = 1200.0
    max_fall = 600.0
    jump_speed = 380.0
    on_ground = True
    coyote_time = 0.08
    coyote_left = 0.0

    # Skills / Stats
    strength_lvl = 1
    endurance_lvl = 0
    speed_lvl = 0
    skill_points = 0
    mined_count_for_skill = 0

    hp_max = hp_for_strength(strength_lvl)
    hp = float(hp_max)
    hp_regen_cd = 0.0

    stam_max = stam_for_endurance(endurance_lvl)
    stam = float(stam_max)
    stam_regen_cooldown = 0.0

    coins = 30  # starting coins (shop scene will change this)

    camera_x = 0
    camera_y = 0

    mining_effects = {}

    # Inventory (resources & potions)
    inventory: dict[str, int] = {}

    # Owned tools with shared durability (None=infinite)
    tools_owned: dict[str, float | None] = {
        "hand": None,
        "wood_pick": float(TOOL_MAX_DUR["wood_pick"]),
    }

    # Hotbar
    hotbar: list[str | None] = ["hand", "wood_pick", None, None]
    selected_slot = 0

    # Minimap cache
    minimap = build_minimap(world, revealed)
    minimap_dirty = False
    minimap_open = False

    # Panels toggles
    inventory_open = False
    skills_open = False

    # Fog drawer
    def draw_fog():
        start_x = camera_x // TILE_SIZE
        end_x = (camera_x + SCREEN_WIDTH) // TILE_SIZE + 1
        start_y = camera_y // TILE_SIZE
        end_y = (camera_y + SCREEN_HEIGHT) // TILE_SIZE + 1
        for tx in range(start_x, end_x):
            for ty in range(max(start_y, SURFACE_LEVEL), end_y):
                if 0 <= tx < WORLD_WIDTH and 0 <= ty < WORLD_HEIGHT:
                    if not revealed[tx][ty]:
                        rect = pygame.Rect(tx * TILE_SIZE - camera_x, ty * TILE_SIZE - camera_y, TILE_SIZE, TILE_SIZE)
                        screen.blit(fog_tile, rect.topleft)

    def add_item(item_id: str, amount: int = 1):
        nonlocal minimap_dirty
        if item_id not in ITEMS:
            return False
        cap = capacity_for_strength(strength_lvl)
        if total_items(inventory) + amount > cap and ITEMS[item_id]["type"] != "consumable":
            return False
        inventory[item_id] = inventory.get(item_id, 0) + amount
        minimap_dirty = True
        return True

    def tile_to_item(tile_type: str) -> str | None:
        return {
            GRASS: "grass_item",
            DIRT: "dirt_item",
            STONE: "stone_item",
            COAL: "coal_item",
            COPPER: "copper_item",
            IRON: "iron_item",
            GOLD: "gold_item",
            EMERALD: "emerald_item",
            DIAMOND: "diamond_item",
        }.get(tile_type, None)

    def adjusted_mining_time(tile_type: str) -> float:
        tool = hotbar[selected_slot] or "hand"
        if tool not in tools_owned or (TOOL_MAX_DUR.get(tool) and (tools_owned[tool] or 0) <= 0):
            tool = "hand"
        base = mining_time_for(tile_type)
        factor = current_tool_factor(tool, tile_type)
        speed_bonus = 1.0 + speed_lvl * SPEED_MINING_BONUS_PER_LVL
        return base / (factor * speed_bonus)

    def take_damage(amount: float):
        nonlocal hp, hp_regen_cd
        hp = max(0.0, hp - amount)
        hp_regen_cd = HP_REGEN_DELAY

    def apply_tool_wear_on_mine(tile_type: str):
        tool = hotbar[selected_slot] or "hand"
        if tool not in tools_owned:
            return
        mx = TOOL_MAX_DUR.get(tool)
        if not mx:  # infinite / hand
            return
        base_loss = TOOL_DECAY_PER_BLOCK.get(tile_type, 1.0)
        reduction = max(0.0, 1.0 - endurance_lvl * ENDURANCE_DURA_REDUCT_PER_LVL)
        loss = base_loss * reduction
        tools_owned[tool] = max(0.0, (tools_owned[tool] or 0) - loss)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        if minimap_dirty:
            minimap = build_minimap(world, revealed)
            minimap_dirty = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    selected_slot = {pygame.K_1:0, pygame.K_2:1, pygame.K_3:2, pygame.K_4:3}[event.key]
                elif event.key == pygame.K_i:
                    inventory_open = not inventory_open
                elif event.key == pygame.K_o:
                    skills_open = not skills_open
                elif event.key == pygame.K_m:
                    minimap_open = not minimap_open
                elif event.key == pygame.K_h:
                    take_damage(12.0)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()

                # Shop button = TELEPORT to shop scene (buying only there)
                if SHOP_BTN_RECT.collidepoint(mx, my):
                    if run_shop is None:
                        print("[world] Shop not available (shop_scene.py missing).")
                    else:
                        # Try flexible signatures for state handoff
                        returned = None
                        try:
                            returned = run_shop(screen, coins, inventory, tools_owned)
                        except TypeError:
                            # fall back to legacy signature
                            run_shop(screen)
                        else:
                            # apply returned state if provided
                            if isinstance(returned, (list, tuple)) and len(returned) >= 3:
                                coins, inventory, tools_owned = returned[0], returned[1], returned[2]
                            elif isinstance(returned, dict):
                                coins = returned.get("coins", coins)
                                inventory = returned.get("inventory", inventory)
                                tools_owned = returned.get("tools_owned", tools_owned)

                        # On return, snap safely to surface and rebuild cached UI
                        spawn_player_on_surface(world, player)
                        vy = 0.0
                        on_ground = True
                        player = push_player_out_of_solids(world, player)
                        player, on_ground = snap_player_to_ground(world, player)
                        build_shop_button_ui(screen)
                    continue

                # Minimap small + buttons under it
                mini_rect = draw_minimap_small(screen, minimap)
                btn_w, btn_h, gap = 110, 24, 6
                inv_btn = pygame.Rect(mini_rect.right - btn_w, mini_rect.bottom + 6, btn_w, btn_h)
                skl_btn = pygame.Rect(mini_rect.right - btn_w, inv_btn.bottom + gap, btn_w, btn_h)
                if inv_btn.collidepoint(mx, my):
                    inventory_open = not inventory_open
                    continue
                if skl_btn.collidepoint(mx, my):
                    skills_open = not skills_open
                    continue

                # Inventory / Skills panel clicks (tools & item cells)
                inv_cells, tool_cells = draw_inventory(screen, font, inventory, tools_owned, selected_slot, inventory_open, strength_lvl)
                skill_clicks = draw_skills(screen, font, skills_open, strength_lvl, endurance_lvl, speed_lvl, skill_points)

                consumed = False
                if inventory_open:
                    for cell_rect, tool_id in tool_cells:
                        if cell_rect.collidepoint(mx, my):
                            hotbar[selected_slot] = tool_id
                            consumed = True
                            break
                if not consumed and skills_open and skill_clicks:
                    if skill_clicks.get("str") and skill_clicks["str"].collidepoint(mx, my) and skill_points > 0:
                        skill_points -= 1
                        strength_lvl += 1
                        old = hp_max
                        hp_max = hp_for_strength(strength_lvl)
                        ratio = hp/old if old > 0 else 1.0
                        hp = max(1.0, min(hp_max, ratio*hp_max))
                        consumed = True
                    elif skill_clicks.get("end") and skill_clicks["end"].collidepoint(mx, my) and skill_points > 0:
                        skill_points -= 1
                        endurance_lvl += 1
                        old = stam_max
                        stam_max = stam_for_endurance(endurance_lvl)
                        ratio = stam/old if old > 0 else 1.0
                        stam = max(0.0, min(stam_max, ratio*stam_max))
                        consumed = True
                    elif skill_clicks.get("spd") and skill_clicks["spd"].collidepoint(mx, my) and skill_points > 0:
                        skill_points -= 1
                        speed_lvl += 1
                        consumed = True
                if consumed:
                    continue

                # Mining click
                tx = (mx + camera_x) // TILE_SIZE
                ty = (my + camera_y) // TILE_SIZE
                if 0 <= tx < WORLD_WIDTH and 0 <= ty < WORLD_HEIGHT:
                    tx, ty = int(tx), int(ty)
                    if revealed[tx][ty] and can_mine_tile(player, tx, ty, MINING_RANGE_TILES):
                        tile = world[tx][ty]
                        if tile and tile != BEDROCK:
                            dur = adjusted_mining_time(tile)
                            if math.isfinite(dur):
                                cost = stamina_cost_for_duration(dur)
                                if stam >= cost:
                                    stam -= cost
                                    stam_regen_cooldown = STAM_REGEN_DELAY
                                    if (tx, ty) not in mining_effects:
                                        mining_effects[(tx, ty)] = MiningEffect(tx, ty, dur, tile)

        keys = pygame.key.get_pressed()

        # Horizontal accel/friction
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            vx -= accel * dt
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            vx += accel * dt
        else:
            if vx > 0:   vx = max(0.0, vx - friction * dt)
            elif vx < 0: vx = min(0.0, vx + friction * dt)
        vx = max(-max_speed, min(max_speed, vx))

        # Jump (coyote)
        if on_ground: coyote_left = coyote_time
        else: coyote_left = max(0.0, coyote_left - dt)
        want_jump = (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE])
        if want_jump and (on_ground or coyote_left > 0.0):
            vy = -jump_speed
            on_ground = False
            coyote_left = 0.0

        # Gravity
        vy = min(max_fall, vy + gravity * dt)

        # Move & collide: X
        new_rect = player.copy()
        new_rect.x += int(round(vx * dt))
        x_start, x_end, y_start, y_end = tiles_overlapping_aabb(new_rect)
        if new_rect.x != player.x:
            step_right = new_rect.x > player.x
            collided = False
            for ty in range(y_start, y_end):
                for tx in range(x_start, x_end):
                    if not solid_at(world, tx, ty): continue
                    tile_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if new_rect.colliderect(tile_rect):
                        collided = True
                        if step_right: new_rect.right = tile_rect.left
                        else: new_rect.left = tile_rect.right
                        vx = 0.0
                        break
                if collided: break
        player.x = new_rect.x

        # Move & collide: Y
        new_rect = player.copy()
        new_rect.y += int(round(vy * dt))
        x_start, x_end, y_start, y_end = tiles_overlapping_aabb(new_rect)
        on_ground = False
        if new_rect.y != player.y:
            step_down = new_rect.y > player.y
            collided = False
            for tx in range(x_start, x_end):
                for ty in range(y_start, y_end):
                    if not solid_at(world, tx, ty): continue
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
                if collided: break
        player.y = new_rect.y

        # Camera
        camera_x = max(0, min(player.centerx - SCREEN_WIDTH // 2, WORLD_WIDTH * TILE_SIZE - SCREEN_WIDTH))
        camera_y = max(0, min(player.centery - SCREEN_HEIGHT // 2, WORLD_HEIGHT * TILE_SIZE - SCREEN_HEIGHT))

        # Mining effects update
        finished_coords = []
        for (tx, ty), eff in list(mining_effects.items()):
            if eff.update(dt):
                if 0 <= tx < WORLD_WIDTH and 0 <= ty < WORLD_HEIGHT and world[tx][ty]:
                    tile_type = world[tx][ty]
                    world[tx][ty] = None
                    reveal_tile(revealed, tx, ty)
                    reveal_neighbors4(revealed, tx, ty)
                    # Give resource
                    item_id = tile_to_item(tile_type)
                    if item_id:
                        add_item(item_id, 1)
                    minimap_dirty = True
                    # Tool wear
                    apply_tool_wear_on_mine(tile_type)
                    # Skill point progression
                    mined_count_for_skill += 1
                    if mined_count_for_skill >= 15:
                        mined_count_for_skill = 0
                        skill_points += 1
                finished_coords.append((tx, ty))
        for key in finished_coords:
            mining_effects.pop(key, None)

        # Stamina regen (with delay)
        if stam_regen_cooldown > 0.0:
            stam_regen_cooldown = max(0.0, stam_regen_cooldown - dt)
        else:
            regen = stamina_regen_rate(stam, stam_max)
            stam = min(stam_max, max(0.0, stam + regen * dt))

        # Health regen (with delay)
        if hp_regen_cd > 0.0:
            hp_regen_cd = max(0.0, hp_regen_cd - dt)
        else:
            if hp < hp_max:
                hregen = health_regen_rate(hp, hp_max)
                hp = min(hp_max, hp + hregen * dt)

        # Draw world
        screen.fill(SKY_BLUE)
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
                        surf = pick_variant_surface(tile, tx, ty, tile_variants)
                        if surf is not None:
                            screen.blit(surf, rect.topleft)
                    eff = mining_effects.get((tx, ty))
                    if eff and (ty < SURFACE_LEVEL or revealed[tx][ty]):
                        eff.draw(screen, camera_x, camera_y)

        # Fog
        if not FOG_BLOCKS_PLAYER:
            draw_fog()

        # Player
        pygame.draw.rect(
            screen, (255, 255, 0),
            pygame.Rect(player.x - camera_x, player.y - camera_y, player.width, player.height)
        )

        # Bars
        draw_player_bars(screen, camera_x, camera_y, player, hp, hp_max, stam, stam_max)

        if FOG_BLOCKS_PLAYER:
            draw_fog()

        # Minimap small + buttons under it
        mini_rect = draw_minimap_small(screen, minimap)
        btn_w, btn_h, gap = 110, 24, 6
        inv_btn = pygame.Rect(mini_rect.right - btn_w, mini_rect.bottom + 6, btn_w, btn_h)
        skl_btn = pygame.Rect(mini_rect.right - btn_w, inv_btn.bottom + gap, btn_w, btn_h)
        for rect, text in [(inv_btn, "Inventory (I)"), (skl_btn, "Skills (O)")]:
            pygame.draw.rect(screen, (22,22,22), rect, border_radius=6)
            pygame.draw.rect(screen, (90,90,90), rect, 1, border_radius=6)
            lab = font.render(text, True, (235,235,235))
            screen.blit(lab, (rect.centerx - lab.get_width()//2, rect.centery - lab.get_height()//2))

        # Cached GUI (Shop button)
        if SHOP_UI_SURF is not None:
            screen.blit(SHOP_UI_SURF, (0, 0))
        # Coins text to the right of Shop button (dynamic)
        coin_rect = pygame.Rect(SHOP_BTN_RECT.right + 8, SHOP_BTN_RECT.y, 180, SHOP_BTN_RECT.height)
        c_txt = big_font.render(f"Coins: {coins}", True, (245, 230, 120))
        screen.blit(c_txt, (coin_rect.x, coin_rect.y + (coin_rect.height - c_txt.get_height())//2))

        # Hotbar (always)
        draw_hotbar(screen, font, hotbar, selected_slot)

        # Panels
        inv_cells, tool_cells = draw_inventory(screen, font, inventory, tools_owned, selected_slot, inventory_open, strength_lvl)
        skill_clicks = draw_skills(screen, font, skills_open, strength_lvl, endurance_lvl, speed_lvl, skill_points)

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    main()
