# -----------------------------------------------------------------------------
#  Tax Season Invaders  -  Community Tax
#  WASM / Browser build  (Pygbag-compatible)
#
#  HOW TO BUILD:
#    pip install pygbag
#    pygbag --build .
#    The ready-to-deploy bundle will be placed in  build/web/
#
#  HOW TO RUN LOCALLY (dev server):
#    pygbag .
#    Then open  http://localhost:8000  in your browser.
#
#  KEY DIFFERENCES from game.py:
#    ? asyncio is imported and main() is async
#    ? MenuScene.run() and GameScene.run() are async;
#      every while-loop iteration yields with  await asyncio.sleep(0)
#      so the browser event-loop is never blocked.
#    ? sys.exit() is removed (not available in WASM); the outer loop just ends.
#    ? The "QUIT" menu option restarts to the menu instead of exiting
#      (browsers cannot be closed programmatically).
# -----------------------------------------------------------------------------

import asyncio
import pygame
import random
import math

# ---------------------------------------------
#  GLOBAL CONFIGURATION
# ---------------------------------------------
SCREEN_W, SCREEN_H = 900, 700
FPS = 60
TITLE = "Tax Season Invaders"

# Colors
BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
DARK_BG     = (8,   8,  24)
GRID_COLOR  = (15,  15,  40)
RED         = (220,  50,  50)
GREEN       = (60,  220, 100)
CYAN        = (0,  210, 255)
YELLOW      = (255, 220,  50)
ORANGE      = (255, 140,  30)
PURPLE      = (160,  60, 220)
LIGHT_GRAY  = (180, 180, 200)
DARK_GRAY   = (50,   50,  70)
DOC_CREAM   = (255, 245, 210)
DOC_LINE    = (180, 150, 100)
DOC_DARK    = (120, 90,  50)
SEAL_RED    = (190,  30,  30)
PLASMA      = (120, 255, 200)
PLASMA_DIM  = (40,  140, 100)

# Game
MAX_LIVES = 5
ENEMY_ROWS = 4
ENEMY_COLS = 10
ENEMY_W, ENEMY_H = 52, 44
ENEMY_GAP_X, ENEMY_GAP_Y = 14, 12
PLAYER_SPEED = 6
BULLET_SPEED = 10
ENEMY_BULLET_SPEED = 5
ENEMY_SHOOT_CHANCE = 0.0018  # per frame per enemy


# ---------------------------------------------
#  SPRITE DRAWING FUNCTIONS
# ---------------------------------------------

# Lazy font cache for sprite number labels (avoids font creation every frame)
_SPRITE_FONTS: dict = {}

def _sprite_font(size: int):
    """Return a cached small font for use inside sprite draw functions."""
    if size not in _SPRITE_FONTS:
        try:
            _SPRITE_FONTS[size] = pygame.font.SysFont("Consolas", size, bold=True)
        except Exception:
            _SPRITE_FONTS[size] = pygame.font.Font(None, size)
    return _SPRITE_FONTS[size]


def draw_player(surface, x, y, color=CYAN):
    """Generic laser cannon (hexagonal + base)."""
    cx = x + 26
    # Base
    pygame.draw.rect(surface, color, (x + 4, y + 38, 44, 10), border_radius=3)
    # Body
    pts_body = [
        (cx - 22, y + 38),
        (cx - 14, y + 20),
        (cx - 8,  y + 20),
        (cx - 8,  y + 10),
        (cx + 8,  y + 10),
        (cx + 8,  y + 20),
        (cx + 14, y + 20),
        (cx + 22, y + 38),
    ]
    pygame.draw.polygon(surface, color, pts_body)
    # Cannon
    pygame.draw.rect(surface, WHITE, (cx - 3, y, 6, 14), border_radius=2)
    # Decorative lights
    pygame.draw.circle(surface, WHITE, (cx - 10, y + 30), 3)
    pygame.draw.circle(surface, WHITE, (cx + 10, y + 30), 3)
    # Outline
    pygame.draw.polygon(surface, WHITE, pts_body, 1)


def draw_document_enemy(surface, x, y, enemy_type=0, frame=0):
    """
    IRS tax-form shaped enemy.
    enemy_type: 0=Form 1040 (40 pts), 1=Form W-2 (30 pts),
                2=Form 1099 (20 pts),  3=Form W-4 (10 pts)
    frame: 0 or 1 for bobbing animation
    """
    bob = 2 if frame == 1 else 0   # vertical bounce
    f14 = _sprite_font(14)
    f11 = _sprite_font(11)

    if enemy_type == 0:
        # -- FORM 1040  (most important - red/white, IRS style)
        ey = y + bob
        pygame.draw.rect(surface, (245, 245, 255), (x + 4, ey + 2, 44, 40), border_radius=2)
        pygame.draw.rect(surface, (200, 30, 30), (x + 4, ey + 2, 44, 11), border_radius=2)
        lbl = f14.render("1040", True, WHITE)
        surface.blit(lbl, (x + 7, ey + 3))
        irs = f11.render("U.S. IRS", True, (160, 30, 30))
        surface.blit(irs, (x + 6, ey + 15))
        for i in range(3):
            pygame.draw.rect(surface, (180, 180, 220), (x + 6, ey + 24 + i * 6, 38, 3))
        pygame.draw.rect(surface, (140, 20, 20), (x + 4, ey + 2, 44, 40), 1, border_radius=2)

    elif enemy_type == 1:
        # -- FORM W-2  (green tinted - wage statement)
        ey = y + bob
        pygame.draw.rect(surface, (220, 245, 220), (x + 5, ey + 2, 42, 40), border_radius=2)
        pygame.draw.rect(surface, (20, 110, 50), (x + 5, ey + 2, 42, 11), border_radius=2)
        lbl = f14.render("W-2", True, WHITE)
        surface.blit(lbl, (x + 11, ey + 3))
        for row in range(2):
            for col in range(3):
                pygame.draw.rect(surface, (60, 140, 80),
                                 (x + 7 + col * 13, ey + 16 + row * 11, 11, 9), 1)
        pygame.draw.rect(surface, (20, 90, 40), (x + 5, ey + 2, 42, 40), 1, border_radius=2)

    elif enemy_type == 2:
        # -- FORM 1099  (blue/buff - miscellaneous income)
        ey = y + bob
        pygame.draw.rect(surface, (255, 248, 200), (x + 5, ey + 2, 42, 40), border_radius=2)
        pygame.draw.rect(surface, (30, 80, 180), (x + 5, ey + 2, 42, 11), border_radius=2)
        lbl = f14.render("1099", True, WHITE)
        surface.blit(lbl, (x + 7, ey + 3))
        for i in range(4):
            pygame.draw.rect(surface, (160, 140, 60), (x + 7, ey + 16 + i * 6, 36, 3))
        pygame.draw.rect(surface, (20, 60, 140), (x + 5, ey + 2, 42, 40), 1, border_radius=2)

    else:
        # -- FORM W-4  (purple/lavender - employee withholding)
        ey = y + bob
        pygame.draw.rect(surface, (238, 225, 255), (x + 5, ey + 2, 42, 40), border_radius=2)
        pygame.draw.rect(surface, (100, 45, 170), (x + 5, ey + 2, 42, 11), border_radius=2)
        lbl = f14.render("W-4", True, WHITE)
        surface.blit(lbl, (x + 11, ey + 3))
        for i in range(2):
            pygame.draw.rect(surface, (140, 100, 190), (x + 7, ey + 16 + i * 9, 36, 3))
        for i in range(3):
            pygame.draw.rect(surface, (120, 70, 170), (x + 8 + i * 12, ey + 28, 8, 7), 1)
        pygame.draw.rect(surface, (120, 70, 170), (x + 7, ey + 38, 36, 2))
        pygame.draw.rect(surface, (80, 35, 140), (x + 5, ey + 2, 42, 40), 1, border_radius=2)


def draw_bullet_player(surface, x, y):
    pygame.draw.rect(surface, PLASMA, (x - 2, y - 8, 4, 14), border_radius=2)
    pygame.draw.rect(surface, WHITE, (x - 1, y - 8, 2, 6))


def draw_bullet_enemy(surface, x, y):
    pygame.draw.rect(surface, RED, (x - 2, y, 4, 12), border_radius=2)
    pygame.draw.circle(surface, ORANGE, (x, y + 3), 3)


def draw_shield(surface, x, y, health):
    if health <= 0:
        return
    col = (0, min(255, 80 + health * 50), min(255, 120 + health * 40))
    pts = [
        (x, y + 20), (x, y + 8), (x + 8, y),
        (x + 44, y), (x + 52, y + 8), (x + 52, y + 20),
        (x + 40, y + 28), (x + 12, y + 28)
    ]
    pygame.draw.polygon(surface, col, pts)
    pygame.draw.polygon(surface, WHITE, pts, 1)


def draw_explosion(surface, x, y, radius):
    pygame.draw.circle(surface, ORANGE, (x, y), radius)
    pygame.draw.circle(surface, YELLOW, (x, y), max(1, radius - 4))
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        ex = int(x + math.cos(rad) * (radius + 4))
        ey = int(y + math.sin(rad) * (radius + 4))
        pygame.draw.circle(surface, RED, (ex, ey), max(1, radius // 3))


# ---------------------------------------------
#  MAIN CLASSES
# ---------------------------------------------

class Particle:
    def __init__(self, x, y):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 5)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(15, 35)
        self.max_life = self.life
        self.color = random.choice([ORANGE, YELLOW, RED, WHITE])
        self.size = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.12
        self.life -= 1

    def draw(self, surface):
        r, g, b = self.color
        col = (min(r, 255), min(g, 255), min(b, 255))
        pygame.draw.circle(surface, col, (int(self.x), int(self.y)), self.size)


class Player:
    W, H = 52, 50

    def __init__(self):
        self.x = SCREEN_W // 2 - self.W // 2
        self.y = SCREEN_H - 80
        self.lives = MAX_LIVES
        self.score = 0
        self.shoot_cooldown = 0
        self.invincible = 0     # invulnerability frames
        self.color = CYAN

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.W, self.H)

    def move(self, dx):
        self.x = max(0, min(SCREEN_W - self.W, self.x + dx * PLAYER_SPEED))

    def can_shoot(self):
        return self.shoot_cooldown <= 0

    def shoot(self):
        self.shoot_cooldown = 18
        return PlayerBullet(self.x + self.W // 2, self.y)

    def hit(self):
        if self.invincible > 0:
            return False
        self.lives -= 1
        self.invincible = 90
        return True

    def update(self):
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.invincible > 0:
            self.invincible -= 1

    def draw(self, surface):
        if self.invincible > 0 and (self.invincible // 8) % 2 == 1:
            return  # blink during invulnerability
        draw_player(surface, self.x, self.y, self.color)


class Enemy:
    W, H = ENEMY_W, ENEMY_H

    def __init__(self, col, row):
        self.col = col
        self.row = row
        self.alive = True
        self.anim_frame = 0
        self.anim_timer = 0
        self.x = 0
        self.y = 0
        # Enemy type based on row: 0=Form 1040, 1=Form W-2, 2=Form 1099, 3=Form W-4
        self.etype = row % 4
        # Points based on row (top rows are worth more)
        self.points = (ENEMY_ROWS - row) * 10

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.W, self.H)

    def update_anim(self):
        self.anim_timer += 1
        if self.anim_timer >= 25:
            self.anim_timer = 0
            self.anim_frame = 1 - self.anim_frame

    def draw(self, surface):
        if self.alive:
            draw_document_enemy(surface, self.x, self.y, self.etype, self.anim_frame)


class EnemyGrid:
    def __init__(self):
        self.enemies = []
        self.dx = 1          # horizontal direction
        self.dy = 0
        self.speed = 1.0
        self.move_timer = 0
        self.move_interval = 38  # frames between moves
        self.descend = False
        self._build()

    def _build(self):
        self.enemies = []
        ox = (SCREEN_W - (ENEMY_COLS * (ENEMY_W + ENEMY_GAP_X))) // 2
        oy = 80
        for row in range(ENEMY_ROWS):
            for col in range(ENEMY_COLS):
                e = Enemy(col, row)
                e.x = ox + col * (ENEMY_W + ENEMY_GAP_X)
                e.y = oy + row * (ENEMY_H + ENEMY_GAP_Y)
                self.enemies.append(e)

    @property
    def alive_enemies(self):
        return [e for e in self.enemies if e.alive]

    def update(self):
        alive = self.alive_enemies
        if not alive:
            return
        self.move_timer += 1
        # Increase speed as fewer enemies remain
        n = len(alive)
        total = ENEMY_ROWS * ENEMY_COLS
        self.move_interval = max(8, int(38 - (total - n) * 0.8))

        if self.descend:
            for e in alive:
                e.y += 14
                e.update_anim()
            self.descend = False
            self.dx *= -1
            self.move_timer = 0
            return

        if self.move_timer >= self.move_interval:
            self.move_timer = 0
            # Check borders
            xs = [e.x for e in alive]
            if self.dx > 0 and max(xs) + ENEMY_W >= SCREEN_W - 10:
                self.descend = True
            elif self.dx < 0 and min(xs) <= 10:
                self.descend = True
            else:
                for e in alive:
                    e.x += self.dx * 18
                    e.update_anim()

    def maybe_shoot(self):
        alive = self.alive_enemies
        bullets = []
        for e in alive:
            if random.random() < ENEMY_SHOOT_CHANCE:
                bullets.append(EnemyBullet(e.x + e.W // 2, e.y + e.H))
        return bullets

    def has_reached_bottom(self):
        for e in self.alive_enemies:
            if e.y + e.H >= SCREEN_H - 90:
                return True
        return False


class PlayerBullet:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.active = True

    @property
    def rect(self):
        return pygame.Rect(self.x - 2, self.y - 8, 4, 14)

    def update(self):
        self.y -= BULLET_SPEED
        if self.y < -20:
            self.active = False

    def draw(self, surface):
        draw_bullet_player(surface, self.x, self.y)


class EnemyBullet:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.active = True

    @property
    def rect(self):
        return pygame.Rect(self.x - 2, self.y, 4, 12)

    def update(self):
        self.y += ENEMY_BULLET_SPEED
        if self.y > SCREEN_H + 20:
            self.active = False

    def draw(self, surface):
        draw_bullet_enemy(surface, self.x, self.y)


class Shield:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.health = 3

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, 52, 28)

    def draw(self, surface):
        draw_shield(surface, self.x, self.y, self.health)


# ---------------------------------------------
#  BACKGROUND STARS
# ---------------------------------------------
class StarField:
    def __init__(self, count=120):
        self.stars = [
            (random.randint(0, SCREEN_W),
             random.randint(0, SCREEN_H),
             random.uniform(0.4, 2.2),
             random.choice([WHITE, LIGHT_GRAY, CYAN, (180, 180, 255)]))
            for _ in range(count)
        ]

    def draw(self, surface):
        for sx, sy, size, col in self.stars:
            r = max(1, int(size))
            pygame.draw.circle(surface, col, (sx, sy), r)


# ---------------------------------------------
#  SCENES  (async - WASM compatible)
# ---------------------------------------------

class MenuScene:
    def __init__(self, screen, clock, fonts):
        self.screen = screen
        self.clock = clock
        self.fonts = fonts
        self.stars = StarField(150)
        self.t = 0
        self.selected = 0
        # In WASM the browser tab cannot be closed, so "QUIT" restarts the menu.
        self.options = ["START GAME", "RESTART MENU"]
        self.result = None   # 'play' | 'quit'

    async def run(self):
        """Async loop - yields to browser every frame via asyncio.sleep(0)."""
        while self.result is None:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.result = 'quit'
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.selected = (self.selected - 1) % len(self.options)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.selected = (self.selected + 1) % len(self.options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.selected == 0:
                            self.result = 'play'
                        else:
                            self.result = 'quit'
            self._draw()
            await asyncio.sleep(0)   # <- yield to browser event loop
        return self.result

    def _draw(self):
        self.t += 1
        self.screen.fill(DARK_BG)
        self._draw_grid()
        self.stars.draw(self.screen)
        self._draw_title()
        self._draw_enemies_preview()
        self._draw_menu()
        self._draw_controls()
        pygame.display.flip()

    def _draw_grid(self):
        for gx in range(0, SCREEN_W, 60):
            pygame.draw.line(self.screen, GRID_COLOR, (gx, 0), (gx, SCREEN_H))
        for gy in range(0, SCREEN_H, 60):
            pygame.draw.line(self.screen, GRID_COLOR, (0, gy), (SCREEN_W, gy))

    def _draw_title(self):
        title_font = self.fonts['title']
        sub_font = self.fonts['sub']
        t1 = title_font.render("TAX SEASON", True, CYAN)
        t2 = title_font.render("INVADERS", True, YELLOW)
        sub = sub_font.render("Community Tax - Defeat every form this tax season!", True, LIGHT_GRAY)
        cx = SCREEN_W // 2
        self.screen.blit(t1, t1.get_rect(center=(cx, 90)))
        self.screen.blit(t2, t2.get_rect(center=(cx, 150)))
        self.screen.blit(sub, sub.get_rect(center=(cx, 200)))

    def _draw_enemies_preview(self):
        etypes = [0, 1, 2, 3]
        labels = ["Form 1040  40 pts", "Form W-2   30 pts", "Form 1099  20 pts", "Form W-4   10 pts"]
        colors = [(245, 80, 80), (100, 200, 120), (100, 160, 255), (180, 130, 255)]
        fx = self.fonts['small']
        for i, (et, label, col) in enumerate(zip(etypes, labels, colors)):
            ex = SCREEN_W // 2 - 200
            ey = 230 + i * 55
            surf = pygame.Surface((ENEMY_W, ENEMY_H), pygame.SRCALPHA)
            draw_document_enemy(surf, 0, 0, et, self.t // 25 % 2)
            scaled = pygame.transform.scale(surf, (38, 34))
            self.screen.blit(scaled, (ex, ey))
            lbl = fx.render(f"= {label}", True, col)
            self.screen.blit(lbl, (ex + 46, ey + 8))

    def _draw_menu(self):
        mfont = self.fonts['menu']
        for i, opt in enumerate(self.options):
            col = YELLOW if i == self.selected else LIGHT_GRAY
            if i == self.selected:
                tw = mfont.size(opt)[0] + 40
                rx = SCREEN_W // 2 - tw // 2
                ry = 475 + i * 60 - 10
                pygame.draw.rect(self.screen, (20, 20, 50), (rx, ry, tw, 46), border_radius=8)
                pygame.draw.rect(self.screen, CYAN, (rx, ry, tw, 46), 2, border_radius=8)
                arrow = mfont.render(">", True, CYAN)
                self.screen.blit(arrow, (rx - 30, ry + 8))
            txt = mfont.render(opt, True, col)
            self.screen.blit(txt, txt.get_rect(center=(SCREEN_W // 2, 498 + i * 60)))

    def _draw_controls(self):
        sf = self.fonts['tiny']
        hints = ["<- -> : Move    |    SPACE : Shoot    |    ^v : Navigate menu"]
        for i, h in enumerate(hints):
            t = sf.render(h, True, DARK_GRAY)
            self.screen.blit(t, t.get_rect(center=(SCREEN_W // 2, SCREEN_H - 22 + i * 18)))


class GameScene:
    def __init__(self, screen, clock, fonts):
        self.screen = screen
        self.clock = clock
        self.fonts = fonts
        self.stars = StarField(120)
        self._reset()

    def _reset(self):
        self.player = Player()
        self.grid = EnemyGrid()
        self.player_bullets = []
        self.enemy_bullets = []
        self.particles = []
        self.shields = self._make_shields()
        self.wave = 1
        self.t = 0
        self.state = 'playing'   # 'playing' | 'wave_clear' | 'game_over' | 'victory'
        self.wave_timer = 0
        self.score_popups = []   # [(x, y, text, timer)]

    def _make_shields(self):
        shields = []
        n = 4
        gap = SCREEN_W // (n + 1)
        for i in range(n):
            shields.append(Shield(gap * (i + 1) - 26, SCREEN_H - 140))
        return shields

    async def run(self):
        """Async loop - yields to browser every frame via asyncio.sleep(0).
        Returns 'menu' or 'quit'.
        """
        while True:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 'quit'
                elif event.type == pygame.KEYDOWN:
                    if self.state in ('game_over', 'victory'):
                        if event.key == pygame.K_RETURN:
                            return 'menu'
                        elif event.key == pygame.K_ESCAPE:
                            return 'menu'   # no sys.exit in WASM - go to menu
                    elif self.state == 'playing':
                        if event.key == pygame.K_ESCAPE:
                            return 'menu'

            if self.state == 'playing':
                self._update()
            elif self.state == 'wave_clear':
                self._update_wave_clear()

            self._draw()
            await asyncio.sleep(0)   # <- yield to browser event loop

    # -- LOGIC ----------------------------------

    def _update(self):
        self.t += 1

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player.move(-1)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player.move(1)
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP]) and self.player.can_shoot():
            self.player_bullets.append(self.player.shoot())

        self.player.update()

        # Move enemy grid
        self.grid.update()

        # Enemy shots
        new_eb = self.grid.maybe_shoot()
        self.enemy_bullets.extend(new_eb)

        # Update player bullets
        for b in self.player_bullets:
            b.update()
        self.player_bullets = [b for b in self.player_bullets if b.active]

        # Update enemy bullets
        for b in self.enemy_bullets:
            b.update()
        self.enemy_bullets = [b for b in self.enemy_bullets if b.active]

        # Particles
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]

        # Score popups
        self.score_popups = [(x, y - 1, txt, t - 1) for x, y, txt, t in self.score_popups if t > 0]

        # -- Player bullet vs enemy collisions --
        for b in self.player_bullets[:]:
            for e in self.grid.alive_enemies:
                if b.rect.colliderect(e.rect):
                    e.alive = False
                    b.active = False
                    self.player.score += e.points
                    self.score_popups.append((e.x + e.W // 2, e.y, f"+{e.points}", 45))
                    for _ in range(18):
                        self.particles.append(Particle(e.x + e.W // 2, e.y + e.H // 2))
                    break

        # -- Player bullet vs shield collisions --
        for b in self.player_bullets[:]:
            for sh in self.shields:
                if sh.health > 0 and b.rect.colliderect(sh.rect):
                    sh.health -= 1
                    b.active = False
                    break

        # -- Enemy bullet vs shield collisions --
        for b in self.enemy_bullets[:]:
            for sh in self.shields:
                if sh.health > 0 and b.rect.colliderect(sh.rect):
                    sh.health -= 1
                    b.active = False
                    break

        # -- Enemy bullet vs player collisions --
        for b in self.enemy_bullets[:]:
            if b.rect.colliderect(self.player.rect):
                b.active = False
                if self.player.hit():
                    for _ in range(12):
                        self.particles.append(Particle(self.player.x + 26, self.player.y + 25))
                    if self.player.lives <= 0:
                        self.state = 'game_over'
                        return

        # -- Enemies reach the bottom --
        if self.grid.has_reached_bottom():
            self.player.lives = 0
            self.state = 'game_over'
            return

        # -- Wave cleared --
        if not self.grid.alive_enemies:
            self.state = 'wave_clear'
            self.wave_timer = 120

    def _update_wave_clear(self):
        self.wave_timer -= 1
        if self.wave_timer <= 0:
            self.wave += 1
            self.grid = EnemyGrid()
            # Increase difficulty per wave
            self.grid.move_interval = max(10, 38 - self.wave * 3)
            self.player_bullets.clear()
            self.enemy_bullets.clear()
            self.shields = self._make_shields()
            self.state = 'playing'

    # -- DRAWING ----------------------------------

    def _draw(self):
        self.screen.fill(DARK_BG)
        self._draw_grid_bg()
        self.stars.draw(self.screen)

        # Shields
        for sh in self.shields:
            sh.draw(self.screen)

        # Enemies
        for e in self.grid.enemies:
            e.draw(self.screen)

        # Player
        self.player.draw(self.screen)

        # Bullets
        for b in self.player_bullets:
            b.draw(self.screen)
        for b in self.enemy_bullets:
            b.draw(self.screen)

        # Particles
        for p in self.particles:
            p.draw(self.screen)

        # Score popups
        pfont = self.fonts['small']
        for x, y, txt, t in self.score_popups:
            tc = pfont.render(txt, True, YELLOW)
            self.screen.blit(tc, tc.get_rect(center=(x, y)))

        # HUD
        self._draw_hud()

        # Overlays
        if self.state == 'wave_clear':
            self._draw_wave_clear()
        elif self.state == 'game_over':
            self._draw_game_over()
        elif self.state == 'victory':
            self._draw_game_over(victory=True)

        pygame.display.flip()

    def _draw_grid_bg(self):
        for gx in range(0, SCREEN_W, 60):
            pygame.draw.line(self.screen, GRID_COLOR, (gx, 0), (gx, SCREEN_H))
        for gy in range(0, SCREEN_H, 60):
            pygame.draw.line(self.screen, GRID_COLOR, (0, gy), (SCREEN_W, gy))

    def _draw_hud(self):
        # Top bar
        pygame.draw.rect(self.screen, (12, 12, 35), (0, 0, SCREEN_W, 44))
        pygame.draw.line(self.screen, CYAN, (0, 44), (SCREEN_W, 44), 1)

        sf = self.fonts['hud']
        # Score
        score_txt = sf.render(f"SCORE: {self.player.score:06d}", True, YELLOW)
        self.screen.blit(score_txt, (16, 10))

        # Wave
        wave_txt = sf.render(f"WAVE: {self.wave}", True, CYAN)
        self.screen.blit(wave_txt, wave_txt.get_rect(center=(SCREEN_W // 2, 22)))

        # Lives
        lives_txt = sf.render("LIVES:", True, LIGHT_GRAY)
        self.screen.blit(lives_txt, (SCREEN_W - 220, 10))
        for i in range(MAX_LIVES):
            col = GREEN if i < self.player.lives else DARK_GRAY
            draw_player(self.screen, SCREEN_W - 160 + i * 28, -8, col)

        # Bottom line of play area
        pygame.draw.line(self.screen, CYAN, (0, SCREEN_H - 50), (SCREEN_W, SCREEN_H - 50), 1)

    def _draw_wave_clear(self):
        self.t += 1
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 80))
        self.screen.blit(overlay, (0, 0))
        f = self.fonts['big']
        sf = self.fonts['sub']
        t1 = f.render(f"WAVE {self.wave} CLEARED", True, GREEN)
        t2 = sf.render(f"PREPARING WAVE {self.wave + 1}...", True, YELLOW)
        self.screen.blit(t1, t1.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 30)))
        self.screen.blit(t2, t2.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 30)))

    def _draw_game_over(self, victory=False):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        tf = self.fonts['title']
        sf = self.fonts['sub']
        mf = self.fonts['menu']

        if victory:
            msg = "VICTORY!"
            col = YELLOW
        else:
            msg = "GAME OVER"
            col = RED

        t1 = tf.render(msg, True, col)
        t2 = sf.render(f"FINAL SCORE:  {self.player.score:06d}", True, WHITE)
        t3 = mf.render("ENTER -> Main Menu", True, CYAN)
        t4 = mf.render("ESC -> Main Menu", True, LIGHT_GRAY)

        self.screen.blit(t1, t1.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 100)))
        self.screen.blit(t2, t2.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2)))
        self.screen.blit(t3, t3.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 80)))
        self.screen.blit(t4, t4.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 130)))


# ---------------------------------------------
#  ENTRY POINT  (async - required by Pygbag)
# ---------------------------------------------

async def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    # Try to load a system font; fall back to default if unavailable
    def load_font(size, bold=False):
        for name in ("Consolas", "Courier New", "monospace", None):
            try:
                return pygame.font.SysFont(name, size, bold=bold)
            except Exception:
                continue
        return pygame.font.Font(None, size)

    fonts = {
        'title': load_font(68,  bold=True),
        'big':   load_font(52,  bold=True),
        'sub':   load_font(30,  bold=False),
        'menu':  load_font(32,  bold=True),
        'hud':   load_font(24,  bold=True),
        'small': load_font(20,  bold=False),
        'tiny':  load_font(18,  bold=False),
    }

    # Outer loop: menu -> game -> menu -> ?
    # In WASM there is no exit, so we loop forever.
    while True:
        menu = MenuScene(screen, clock, fonts)
        action = await menu.run()
        if action == 'quit':
            # Can't close the tab - just restart the menu loop
            continue
        game = GameScene(screen, clock, fonts)
        await game.run()
        # After any game result (menu / quit), return to menu

    pygame.quit()


# Pygbag requires asyncio.run() at module level
asyncio.run(main())
