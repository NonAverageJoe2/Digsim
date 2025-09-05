import pygame
import math
from typing import Tuple, List, Dict, Optional

# ---------- Enhanced shop with tabbed panel and skill requirements ----------

ROOM_TILES = (24, 16)   # width, height in tiles
TILE_SIZE  = 32
PLAYER_SIZE = (20, 20)
PLAYER_SPEED = 200.0
PLAYER_ACCEL = 1600.0
PLAYER_FRICTION = 2000.0

# Colors
WOOD_BASE   = (92, 72, 55)
WOOD_LIGHT  = (122, 98, 75)
WOOD_DARK   = (65, 50, 37)
WALL_COLOR  = (45, 35, 27)
COUNTER_COLOR = (65, 50, 38)
CARPET_COLOR = (120, 40, 40)
UI_BG       = (20, 20, 20)
UI_PANEL_BG = (25, 25, 25)
UI_FG       = (240, 240, 240)
TAB_ACTIVE  = (70, 70, 70)
TAB_INACTIVE = (40, 40, 40)
BUTTON_BG   = (50, 50, 50)
BUTTON_HOVER = (70, 70, 70)
REQ_MET_COLOR = (100, 200, 100)
REQ_NOT_MET_COLOR = (200, 100, 100)
COIN_COLOR = (245, 230, 120)

# Shop Panel Settings
PANEL_WIDTH = 600
PANEL_HEIGHT = 450
TAB_HEIGHT = 40
ITEM_HEIGHT = 70

# Shop data -----------------------------------------------------------------

# Tools for sale (id, label, price, requirements)
# Requirements: dict of skill_name -> level_required (None = no requirements)
BUY_ITEMS = [
    ("wood_shovel", "Wood Shovel", 25, None),
    ("stone_pick", "Stone Pickaxe", 45, {"strength": 2}),
    ("sword", "Sword", 60, {"strength": 3, "speed": 2}),
    ("metal_shovel", "Metal Shovel", 80, {"strength": 5, "endurance": 5, "speed": 5}),
    ("metal_pick", "Metal Pickaxe", 120, {"strength": 5, "endurance": 5, "speed": 5}),
    ("hp_potion", "HP Potion", 15, None),
    ("stam_potion", "Stamina Potion", 12, None),
]

# Durability for tools we can sell
TOOL_MAX = {
    "wood_shovel": 100,
    "metal_shovel": 240,
    "stone_pick": 160,
    "metal_pick": 280,
    "sword": 250,
}

# Resources that can be sold back to the shop
SELL_PRICES = {
    "grass_item":   ("Grass", 1),
    "dirt_item":    ("Dirt", 1),
    "stone_item":   ("Stone", 2),
    "coal_item":    ("Coal", 4),
    "copper_item":  ("Copper", 6),
    "iron_item":    ("Iron", 8),
    "gold_item":    ("Gold", 15),
    "emerald_item": ("Emerald", 25),
    "diamond_item": ("Diamond", 40),
}

# Item colors for icons
ITEM_COLORS = {
    "wood_shovel": (170, 130, 70),
    "metal_shovel": (190, 190, 215),
    "stone_pick": (150, 150, 150),
    "metal_pick": (180, 180, 210),
    "sword": (210, 210, 230),
    "hp_potion": (210, 60, 60),
    "stam_potion": (70, 200, 110),
    # Resources
    "grass_item": (34, 139, 34),
    "dirt_item": (139, 69, 19),
    "stone_item": (128, 128, 128),
    "coal_item": (40, 40, 40),
    "copper_item": (184, 115, 51),
    "iron_item": (190, 190, 190),
    "gold_item": (212, 175, 55),
    "emerald_item": (46, 204, 113),
    "diamond_item": (0, 220, 220),
}

def _make_wood_tile() -> pygame.Surface:
    """Create a wood plank tile."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE)).convert()
    surf.fill(WOOD_BASE)
    # wood grain
    for y in range(0, TILE_SIZE, 4):
        color = WOOD_DARK if (y // 4) % 2 == 0 else WOOD_LIGHT
        pygame.draw.line(surf, color, (0, y), (TILE_SIZE, y), 1)
    # knots
    for _ in range(2):
        import random
        x = random.randint(4, TILE_SIZE - 4)
        y = random.randint(4, TILE_SIZE - 4)
        pygame.draw.circle(surf, WOOD_DARK, (x, y), 2)
        pygame.draw.circle(surf, WOOD_LIGHT, (x, y), 1)
    return surf

def _make_carpet_tile() -> pygame.Surface:
    """Create a carpet tile."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE)).convert()
    surf.fill(CARPET_COLOR)
    # Add texture
    for x in range(0, TILE_SIZE, 2):
        for y in range(0, TILE_SIZE, 2):
            if (x + y) % 4 == 0:
                surf.set_at((x, y), (130, 45, 45))
    return surf

def _tile_fill(dest: pygame.Surface, tile: pygame.Surface) -> None:
    """Fill the entire dest with the given tile surface."""
    tw, th = tile.get_size()
    w, h = dest.get_size()
    for y in range(0, h, th):
        for x in range(0, w, tw):
            dest.blit(tile, (x, y))

def _resolve_collisions(rect: pygame.Rect, obstacles: List[pygame.Rect], vel: pygame.Vector2) -> Tuple[pygame.Rect, pygame.Vector2]:
    """Axis-separated collision resolution."""
    # X movement
    moved = rect.move(int(round(vel.x)), 0)
    for ob in obstacles:
        if moved.colliderect(ob):
            if vel.x > 0:
                moved.right = ob.left
            elif vel.x < 0:
                moved.left = ob.right
            vel.x = 0
    rect = moved
    # Y movement
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
    """Keep player within room bounds."""
    w, h = room_px
    if rect.left < 0: rect.left = 0
    if rect.top < 0: rect.top = 0
    if rect.right > w: rect.right = w
    if rect.bottom > h: rect.bottom = h
    return rect

def draw_item_icon(surf: pygame.Surface, rect: pygame.Rect, item_id: str):
    """Draw an item icon."""
    color = ITEM_COLORS.get(item_id, (128, 128, 128))
    # Simple colored rect with rounded corners
    icon_rect = rect.inflate(-12, -12)
    pygame.draw.rect(surf, color, icon_rect, border_radius=6)
    # Add a subtle highlight
    highlight_rect = pygame.Rect(icon_rect.x + 2, icon_rect.y + 2, icon_rect.width - 4, 4)
    pygame.draw.rect(surf, (255, 255, 255, 30), highlight_rect, border_radius=2)

def check_requirements(requirements: Optional[Dict[str, int]], skills: Dict[str, int]) -> Tuple[bool, List[str]]:
    """Check if skill requirements are met. Returns (met, list of unmet requirements)."""
    if requirements is None:
        return True, []
    
    unmet = []
    for skill, required_level in requirements.items():
        current_level = skills.get(skill, 0)
        if current_level < required_level:
            unmet.append(f"{skill.capitalize()} Lv {required_level} (have {current_level})")
    
    return len(unmet) == 0, unmet

def run_shop(screen: pygame.Surface,
             coins: int,
             inventory: dict[str, int],
             tools_owned: dict[str, float | None],
             skills: Optional[Dict[str, int]] = None) -> tuple[int, dict[str, int], dict[str, float | None]]:
    """Run the enhanced shop scene with tabbed panel and skill requirements.
    
    Args:
        screen: Pygame screen surface
        coins: Current coin count
        inventory: Player's inventory (resources)
        tools_owned: Tools owned by player with durability
        skills: Dict with 'strength', 'endurance', 'speed' levels (optional)
    
    Returns:
        Updated (coins, inventory, tools_owned) tuple
    """
    
    # Default skills if not provided
    if skills is None:
        skills = {"strength": 1, "endurance": 0, "speed": 0}
    
    clock = pygame.time.Clock()
    sw, sh = screen.get_size()
    room_px = (ROOM_TILES[0] * TILE_SIZE, ROOM_TILES[1] * TILE_SIZE)
    
    # Center room if smaller than window
    view_offset = (max(0, (sw - room_px[0]) // 2), max(0, (sh - room_px[1]) // 2))
    
    # Build floor
    floor = pygame.Surface(room_px).convert()
    wood_tile = _make_wood_tile()
    carpet_tile = _make_carpet_tile()
    _tile_fill(floor, wood_tile)
    
    # Add carpet area in center
    carpet_area = pygame.Rect(TILE_SIZE * 8, TILE_SIZE * 6, TILE_SIZE * 8, TILE_SIZE * 4)
    for y in range(carpet_area.y, carpet_area.bottom, TILE_SIZE):
        for x in range(carpet_area.x, carpet_area.right, TILE_SIZE):
            floor.blit(carpet_tile, (x, y))
    
    # Walls (1-tile border)
    walls: List[pygame.Rect] = []
    walls.append(pygame.Rect(0, 0, room_px[0], TILE_SIZE))  # top
    walls.append(pygame.Rect(0, room_px[1] - TILE_SIZE, room_px[0], TILE_SIZE))  # bottom
    walls.append(pygame.Rect(0, 0, TILE_SIZE, room_px[1]))  # left
    walls.append(pygame.Rect(room_px[0] - TILE_SIZE, 0, TILE_SIZE, room_px[1]))  # right
    
    # Shop counters/obstacles
    counters: List[pygame.Rect] = [
        pygame.Rect(TILE_SIZE * 2, TILE_SIZE * 3, TILE_SIZE * 8, TILE_SIZE * 2),  # Top counter
        pygame.Rect(TILE_SIZE * 14, TILE_SIZE * 3, TILE_SIZE * 8, TILE_SIZE * 2),  # Top right counter
        pygame.Rect(TILE_SIZE * 2, TILE_SIZE * 11, TILE_SIZE * 6, TILE_SIZE * 2),  # Bottom left
        pygame.Rect(TILE_SIZE * 16, TILE_SIZE * 11, TILE_SIZE * 6, TILE_SIZE * 2),  # Bottom right
    ]
    
    # Shopkeeper position (behind counter)
    shopkeeper_pos = (TILE_SIZE * 6, TILE_SIZE * 3 - 10)
    
    obstacles = walls + counters
    
    # Fonts
    font = pygame.font.SysFont(None, 24)
    small_font = pygame.font.SysFont(None, 18)
    big_font = pygame.font.SysFont(None, 28)
    
    # Player
    p_rect = pygame.Rect(room_px[0] // 2 - PLAYER_SIZE[0] // 2, 
                         room_px[1] * 0.75 - PLAYER_SIZE[1] // 2,
                         PLAYER_SIZE[0], PLAYER_SIZE[1])
    vel = pygame.Vector2(0, 0)
    player_dir = "down"  # Track direction for sprite
    
    # Shop UI state
    shop_open = False
    current_tab = "buy"  # "buy", "sell", "upgrades"
    scroll_offset = 0
    
    # Exit button
    exit_text = font.render("Exit Shop (Esc)", True, UI_FG)
    exit_rect = pygame.Rect(10, 10, exit_text.get_width() + 16, exit_text.get_height() + 8)
    
    # Shop button (opens panel)
    shop_button_rect = pygame.Rect(sw // 2 - 60, sh - 60, 120, 40)
    
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        mx, my = pygame.mouse.get_pos()
        
        # Panel position
        panel_x = (sw - PANEL_WIDTH) // 2
        panel_y = (sh - PANEL_HEIGHT) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, PANEL_WIDTH, PANEL_HEIGHT)
        
        # Tab rectangles
        tabs = ["Buy", "Sell", "Upgrades"]
        tab_rects = []
        tab_width = PANEL_WIDTH // len(tabs)
        for i, tab_name in enumerate(tabs):
            tab_rects.append(pygame.Rect(panel_x + i * tab_width, panel_y, tab_width, TAB_HEIGHT))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if shop_open:
                        shop_open = False
                    else:
                        return coins, inventory, tools_owned
                elif event.key == pygame.K_e:
                    shop_open = not shop_open
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Exit button
                if exit_rect.collidepoint(mx, my):
                    return coins, inventory, tools_owned
                
                # Shop button
                if not shop_open and shop_button_rect.collidepoint(mx, my):
                    shop_open = True
                
                if shop_open:
                    # Close button (X in corner)
                    close_rect = pygame.Rect(panel_rect.right - 30, panel_rect.y + 5, 25, 25)
                    if close_rect.collidepoint(mx, my):
                        shop_open = False
                    
                    # Tab clicks
                    for i, (tab_rect, tab_name) in enumerate(zip(tab_rects, tabs)):
                        if tab_rect.collidepoint(mx, my):
                            current_tab = tab_name.lower()
                            scroll_offset = 0
                    
                    # Item interactions
                    content_y = panel_y + TAB_HEIGHT + 10
                    
                    if current_tab == "buy":
                        for i, (item_id, label, price, requirements) in enumerate(BUY_ITEMS):
                            item_y = content_y + i * ITEM_HEIGHT - scroll_offset
                            if item_y < panel_y + TAB_HEIGHT or item_y + ITEM_HEIGHT > panel_rect.bottom:
                                continue
                            
                            buy_rect = pygame.Rect(panel_rect.right - 100, item_y + 20, 80, 30)
                            if buy_rect.collidepoint(mx, my):
                                req_met, _ = check_requirements(requirements, skills)
                                if req_met and coins >= price:
                                    coins -= price
                                    if item_id in TOOL_MAX:
                                        tools_owned[item_id] = float(TOOL_MAX[item_id])
                                    else:
                                        # Consumables
                                        inventory[item_id] = inventory.get(item_id, 0) + 1
                    
                    elif current_tab == "sell":
                        idx = 0
                        for item_id, (name, price) in SELL_PRICES.items():
                            if inventory.get(item_id, 0) > 0:
                                item_y = content_y + idx * ITEM_HEIGHT - scroll_offset
                                if item_y >= panel_y + TAB_HEIGHT and item_y + ITEM_HEIGHT <= panel_rect.bottom:
                                    sell_rect = pygame.Rect(panel_rect.right - 100, item_y + 20, 80, 30)
                                    if sell_rect.collidepoint(mx, my):
                                        inventory[item_id] -= 1
                                        if inventory[item_id] <= 0:
                                            inventory.pop(item_id, None)
                                        coins += price
                                idx += 1
            
            elif event.type == pygame.MOUSEWHEEL and shop_open:
                scroll_offset = max(0, scroll_offset - event.y * 30)
        
        # Player movement (only when shop panel is closed)
        if not shop_open:
            keys = pygame.key.get_pressed()
            dir_x = (1 if keys[pygame.K_RIGHT] or keys[pygame.K_d] else 0) - (
                1 if keys[pygame.K_LEFT] or keys[pygame.K_a] else 0)
            dir_y = (1 if keys[pygame.K_DOWN] or keys[pygame.K_s] else 0) - (
                1 if keys[pygame.K_UP] or keys[pygame.K_w] else 0)
            
            # Update direction
            if dir_y < 0: player_dir = "up"
            elif dir_y > 0: player_dir = "down"
            elif dir_x < 0: player_dir = "left"
            elif dir_x > 0: player_dir = "right"
            
            move_dir = pygame.Vector2(dir_x, dir_y)
            if move_dir.length_squared() > 0:
                move_dir = move_dir.normalize()
                target = move_dir * PLAYER_SPEED
                dv = target - vel
                step = PLAYER_ACCEL * dt
                if dv.length() <= step:
                    vel = target
                else:
                    vel += dv.normalize() * step
            else:
                speed = vel.length()
                if speed > 0:
                    drop = PLAYER_FRICTION * dt
                    speed = max(0.0, speed - drop)
                    vel = vel.normalize() * speed if speed > 0 else pygame.Vector2(0, 0)
            
            # Move & collide
            p_rect, vel = _resolve_collisions(p_rect, obstacles, vel * dt)
            p_rect = _clamp_to_room(p_rect, room_px)
        
        # -------- Drawing --------
        screen.fill((15, 15, 15))
        
        # Floor
        screen.blit(floor, view_offset)
        
        # Counters
        for counter in counters:
            rect = counter.move(view_offset)
            # Counter shadow
            shadow_rect = rect.move(2, 2)
            pygame.draw.rect(screen, (0, 0, 0, 100), shadow_rect)
            # Counter surface
            pygame.draw.rect(screen, COUNTER_COLOR, rect)
            # Counter edge highlight
            pygame.draw.rect(screen, WOOD_LIGHT, rect, 2)
        
        # Walls
        for wall in walls:
            pygame.draw.rect(screen, WALL_COLOR, wall.move(view_offset))
        
        # Shopkeeper (simple sprite)
        keeper_rect = pygame.Rect(shopkeeper_pos[0] + view_offset[0], 
                                 shopkeeper_pos[1] + view_offset[1], 24, 30)
        pygame.draw.ellipse(screen, (90, 70, 50), keeper_rect)  # Body
        pygame.draw.circle(screen, (255, 220, 177), 
                          (keeper_rect.centerx, keeper_rect.top + 8), 6)  # Head
        
        # Player
        pr = p_rect.move(view_offset)
        # Shadow
        shadow = pygame.Rect(pr.x + 2, pr.bottom - 4, pr.width - 4, 6)
        pygame.draw.ellipse(screen, (0, 0, 0, 80), shadow)
        # Player body
        pygame.draw.rect(screen, (100, 100, 200), pr)
        pygame.draw.rect(screen, (80, 80, 160), pr, 2)
        # Direction indicator
        if player_dir == "up":
            pygame.draw.circle(screen, (255, 255, 255), (pr.centerx, pr.top + 4), 2)
        elif player_dir == "down":
            pygame.draw.circle(screen, (255, 255, 255), (pr.centerx, pr.bottom - 4), 2)
        elif player_dir == "left":
            pygame.draw.circle(screen, (255, 255, 255), (pr.left + 4, pr.centery), 2)
        elif player_dir == "right":
            pygame.draw.circle(screen, (255, 255, 255), (pr.right - 4, pr.centery), 2)
        
        # UI Elements
        # Exit button
        pygame.draw.rect(screen, (40, 40, 40), exit_rect, border_radius=6)
        screen.blit(exit_text, (exit_rect.x + 8, exit_rect.y + 4))
        
        # Coins display
        coin_text = big_font.render(f"Coins: {coins}", True, COIN_COLOR)
        coin_bg = pygame.Rect(sw // 2 - coin_text.get_width() // 2 - 10, 10, 
                             coin_text.get_width() + 20, coin_text.get_height() + 8)
        pygame.draw.rect(screen, (30, 30, 30), coin_bg, border_radius=8)
        screen.blit(coin_text, (coin_bg.x + 10, coin_bg.y + 4))
        
        # Shop button (when panel is closed)
        if not shop_open:
            hover = shop_button_rect.collidepoint(mx, my)
            pygame.draw.rect(screen, BUTTON_HOVER if hover else BUTTON_BG, 
                           shop_button_rect, border_radius=8)
            pygame.draw.rect(screen, (150, 150, 150), shop_button_rect, 2, border_radius=8)
            shop_text = font.render("Shop (E)", True, UI_FG)
            screen.blit(shop_text, (shop_button_rect.centerx - shop_text.get_width() // 2,
                                   shop_button_rect.centery - shop_text.get_height() // 2))
        
        # Shop Panel
        if shop_open:
            # Dark overlay
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            
            # Panel background
            pygame.draw.rect(screen, UI_PANEL_BG, panel_rect, border_radius=10)
            pygame.draw.rect(screen, (80, 80, 80), panel_rect, 2, border_radius=10)
            
            # Tabs
            for i, (tab_rect, tab_name) in enumerate(zip(tab_rects, tabs)):
                is_active = tab_name.lower() == current_tab
                color = TAB_ACTIVE if is_active else TAB_INACTIVE
                if i == 0:  # First tab
                    pygame.draw.rect(screen, color, tab_rect, border_top_left_radius=10)
                elif i == len(tabs) - 1:  # Last tab
                    pygame.draw.rect(screen, color, tab_rect, border_top_right_radius=10)
                else:
                    pygame.draw.rect(screen, color, tab_rect)
                
                pygame.draw.rect(screen, (100, 100, 100), tab_rect, 1)
                tab_text = font.render(tab_name, True, UI_FG)
                screen.blit(tab_text, (tab_rect.centerx - tab_text.get_width() // 2,
                                      tab_rect.centery - tab_text.get_height() // 2))
            
            # Close button
            close_rect = pygame.Rect(panel_rect.right - 30, panel_rect.y + 5, 25, 25)
            pygame.draw.rect(screen, (200, 50, 50), close_rect, border_radius=4)
            close_text = font.render("X", True, UI_FG)
            screen.blit(close_text, (close_rect.centerx - close_text.get_width() // 2,
                                    close_rect.centery - close_text.get_height() // 2))
            
            # Content area
            content_rect = pygame.Rect(panel_x, panel_y + TAB_HEIGHT, 
                                      PANEL_WIDTH, PANEL_HEIGHT - TAB_HEIGHT)
            
            # Set clip to prevent drawing outside panel
            screen.set_clip(content_rect)
            
            content_y = panel_y + TAB_HEIGHT + 10
            
            if current_tab == "buy":
                for i, (item_id, label, price, requirements) in enumerate(BUY_ITEMS):
                    item_y = content_y + i * ITEM_HEIGHT - scroll_offset
                    if item_y < panel_y + TAB_HEIGHT - ITEM_HEIGHT or item_y > panel_rect.bottom:
                        continue
                    
                    # Item background
                    item_rect = pygame.Rect(panel_x + 10, item_y, PANEL_WIDTH - 20, ITEM_HEIGHT - 5)
                    pygame.draw.rect(screen, (35, 35, 35), item_rect, border_radius=6)
                    
                    # Icon
                    icon_rect = pygame.Rect(item_rect.x + 5, item_rect.y + 10, 50, 50)
                    draw_item_icon(screen, icon_rect, item_id)
                    
                    # Name and price
                    name_text = font.render(label, True, UI_FG)
                    screen.blit(name_text, (icon_rect.right + 15, item_rect.y + 10))
                    
                    price_text = small_font.render(f"Price: {price} coins", True, COIN_COLOR)
                    screen.blit(price_text, (icon_rect.right + 15, item_rect.y + 35))
                    
                    # Requirements
                    req_met, unmet_list = check_requirements(requirements, skills)
                    if requirements:
                        req_color = REQ_MET_COLOR if req_met else REQ_NOT_MET_COLOR
                        if req_met:
                            req_text = small_font.render("Requirements met", True, req_color)
                        else:
                            req_text = small_font.render(f"Requires: {', '.join(unmet_list)}", True, req_color)
                        screen.blit(req_text, (icon_rect.right + 180, item_rect.y + 35))
                    
                    # Buy button
                    buy_rect = pygame.Rect(item_rect.right - 100, item_rect.y + 20, 80, 30)
                    can_buy = req_met and coins >= price
                    button_color = (60, 120, 60) if can_buy else (80, 40, 40)
                    hover = buy_rect.collidepoint(mx, my) and can_buy
                    if hover:
                        button_color = (80, 150, 80)
                    
                    pygame.draw.rect(screen, button_color, buy_rect, border_radius=6)
                    buy_text = small_font.render("Buy", True, UI_FG)
                    screen.blit(buy_text, (buy_rect.centerx - buy_text.get_width() // 2,
                                          buy_rect.centery - buy_text.get_height() // 2))
            
            elif current_tab == "sell":
                idx = 0
                for item_id, (name, price) in SELL_PRICES.items():
                    count = inventory.get(item_id, 0)
                    if count > 0:
                        item_y = content_y + idx * ITEM_HEIGHT - scroll_offset
                        if item_y >= panel_y + TAB_HEIGHT - ITEM_HEIGHT or item_y > panel_rect.bottom:
                            idx += 1
                            continue
                        
                        # Item background
                        item_rect = pygame.Rect(panel_x + 10, item_y, PANEL_WIDTH - 20, ITEM_HEIGHT - 5)
                        pygame.draw.rect(screen, (35, 35, 35), item_rect, border_radius=6)
                        
                        # Icon
                        icon_rect = pygame.Rect(item_rect.x + 5, item_rect.y + 10, 50, 50)
                        draw_item_icon(screen, icon_rect, item_id)
                        
                        # Name and count
                        name_text = font.render(f"{name} x{count}", True, UI_FG)
                        screen.blit(name_text, (icon_rect.right + 15, item_rect.y + 10))
                        
                        price_text = small_font.render(f"Sell for: {price} coins each", True, COIN_COLOR)
                        screen.blit(price_text, (icon_rect.right + 15, item_rect.y + 35))
                        
                        # Sell button
                        sell_rect = pygame.Rect(item_rect.right - 100, item_rect.y + 20, 80, 30)
                        hover = sell_rect.collidepoint(mx, my)
                        button_color = (80, 120, 80) if hover else (60, 100, 60)
                        
                        pygame.draw.rect(screen, button_color, sell_rect, border_radius=6)
                        sell_text = small_font.render("Sell 1", True, UI_FG)
                        screen.blit(sell_text, (sell_rect.centerx - sell_text.get_width() // 2,
                                               sell_rect.centery - sell_text.get_height() // 2))
                        idx += 1
                
                if idx == 0:
                    no_items = font.render("No items to sell", True, (150, 150, 150))
                    screen.blit(no_items, (panel_rect.centerx - no_items.get_width() // 2,
                                          content_y + 50))
            
            elif current_tab == "upgrades":
                coming_soon = big_font.render("Coming Soon!", True, (150, 150, 150))
                screen.blit(coming_soon, (panel_rect.centerx - coming_soon.get_width() // 2,
                                         panel_rect.centery - coming_soon.get_height() // 2))
            
            # Reset clip
            screen.set_clip(None)
        
        # Instructions
        if not shop_open:
            inst_text = small_font.render("Use WASD/Arrows to move, E to open shop", True, (200, 200, 200))
            screen.blit(inst_text, (sw // 2 - inst_text.get_width() // 2, sh - 20))
        
        pygame.display.flip()
    
    return coins, inventory, tools_owned
