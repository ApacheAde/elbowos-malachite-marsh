#!/usr/bin/env python3
"""Malachite Marsh — neon tide-hopper arcade for ElbowOS. Python 3 + pygame."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv

if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/MALACHITE_MARSH_ElbowOS.mp4")
TITLE, HANDLE = "MALACHITE MARSH", "x.com/ElbowOS"

# Palette: deep teal swamp + neon malachite greens, cyan, magenta, gold
BG = (4, 18, 22)
WATER = (8, 40, 48)
LANE_H = 110
PLAYER_Y_START = H - 220
HIT_ZONE = 70

class Lane:
    def __init__(self, y, speed, count, color, is_safe=False):
        self.y = y
        self.speed = speed
        self.color = color
        self.is_safe = is_safe
        self.objs = []
        spacing = W // max(1, count) + 40
        for i in range(count):
            x = (i * spacing + random.randint(0, 80)) % (W + 200) - 100
            self.objs.append({"x": x, "w": random.randint(140, 280), "h": 48})

    def update(self):
        for o in self.objs:
            o["x"] += self.speed
            if self.speed > 0 and o["x"] > W + 50:
                o["x"] = -o["w"] - 20
            elif self.speed < 0 and o["x"] < -o["w"] - 50:
                o["x"] = W + 20

    def draw(self, surf):
        pygame.draw.rect(surf, WATER if not self.is_safe else (6, 28, 32), (0, self.y, W, LANE_H))
        for o in self.objs:
            col = self.color
            pygame.draw.rect(surf, col, (o["x"], self.y + 30, o["w"], o["h"]), border_radius=12)
            # glow edge
            pygame.draw.rect(surf, tuple(min(255, c+60) for c in col), (o["x"], self.y + 30, o["w"], o["h"]), 3, border_radius=12)

    def collides(self, px, py):
        if self.is_safe:
            return False
        for o in self.objs:
            if o["x"] < px + 36 and o["x"] + o["w"] > px - 36 and abs(py - (self.y + 54)) < 40:
                return True
        return False

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            self.screen = pygame.display.set_mode((W, H), pygame.HIDDEN)
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.SysFont("monospace", 72, bold=True)
        self.font_md = pygame.font.SysFont("monospace", 48, bold=True)
        self.font_sm = pygame.font.SysFont("monospace", 32)
        self.reset()

    def reset(self):
        self.px = W // 2
        self.py = PLAYER_Y_START
        self.score = 0
        self.alive = True
        self.lanes = []
        colors = [(0, 220, 160), (0, 255, 200), (80, 255, 120), (255, 80, 200), (255, 200, 40)]
        for i in range(14):
            y = 180 + i * LANE_H
            speed = random.choice([-4.5, -3.2, 3.2, 4.8]) * (1 if i % 2 == 0 else -1)
            count = random.randint(3, 5)
            col = colors[i % len(colors)]
            safe = (i % 4 == 0)
            self.lanes.append(Lane(y, speed if not safe else 0, count if not safe else 0, col, safe))
        self.goal_y = 120
        self.hop_cooldown = 0
        self.auto_timer = 0

    def hop(self, dx=0, dy=-LANE_H):
        if not self.alive or self.hop_cooldown > 0:
            return
        self.px = max(60, min(W - 60, self.px + dx))
        self.py = max(self.goal_y, self.py + dy)
        self.hop_cooldown = 8
        if dy < 0:
            self.score += 10
        if self.py <= self.goal_y + 40:
            self.score += 50
            self.py = PLAYER_Y_START
            # respawn higher progress feel by shifting? keep simple

    def tick(self):
        if self.hop_cooldown > 0:
            self.hop_cooldown -= 1
        for ln in self.lanes:
            ln.update()
            if ln.collides(self.px, self.py):
                self.alive = False
        if not self.alive and self.score > 0:
            pass  # freeze

    def autoplay(self):
        self.auto_timer += 1
        if not self.alive:
            if self.auto_timer % 90 == 0:
                self.reset()
            return
        # simple AI: hop up when gap, occasionally lateral
        if self.auto_timer % 12 == 0:
            # check current lane safety
            safe = True
            for ln in self.lanes:
                if abs(ln.y + 54 - self.py) < 50 and ln.collides(self.px, self.py):
                    safe = False
            if safe or self.auto_timer % 24 == 0:
                dx = random.choice([-80, 0, 80]) if random.random() < 0.3 else 0
                self.hop(dx, -LANE_H)
            elif random.random() < 0.4:
                self.hop(random.choice([-100, 100]), 0)

    def draw(self, surf):
        surf.fill(BG)
        # goal strip
        pygame.draw.rect(surf, (0, 80, 60), (0, 80, W, 60))
        pygame.draw.rect(surf, (0, 255, 180), (0, 80, W, 60), 4)
        # lanes
        for ln in self.lanes:
            ln.draw(surf)
        # player — glowing malachite frog
        col = (0, 255, 140) if self.alive else (180, 40, 40)
        pygame.draw.ellipse(surf, col, (self.px - 36, self.py - 28, 72, 56))
        pygame.draw.ellipse(surf, (20, 20, 20), (self.px - 22, self.py - 14, 16, 16))
        pygame.draw.ellipse(surf, (20, 20, 20), (self.px + 6, self.py - 14, 16, 16))
        # overlays
        title = self.font_lg.render(TITLE, True, (0, 255, 180))
        surf.blit(title, title.get_rect(center=(W // 2, 48)))
        sc = self.font_md.render(f"SCORE {self.score}", True, (255, 220, 80))
        surf.blit(sc, sc.get_rect(center=(W // 2, H - 140)))
        handle = self.font_sm.render(HANDLE, True, (180, 255, 220))
        surf.blit(handle, handle.get_rect(center=(W // 2, H - 80)))
        if not self.alive:
            dead = self.font_lg.render("SPLASH!", True, (255, 80, 100))
            surf.blit(dead, dead.get_rect(center=(W // 2, H // 2)))

    def play_interactive(self):
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_UP, pygame.K_w, pygame.K_SPACE):
                        self.hop(0, -LANE_H)
                    elif ev.key in (pygame.K_DOWN, pygame.K_s):
                        self.hop(0, LANE_H)
                    elif ev.key in (pygame.K_LEFT, pygame.K_a):
                        self.hop(-90, 0)
                    elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                        self.hop(90, 0)
                    elif ev.key == pygame.K_r:
                        self.reset()
            self.tick()
            self.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    def record(self):
        frames = FPS * SECS
        cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-crf", "20", "-preset", "fast", "-movflags", "+faststart", OUT]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        canvas = pygame.Surface((W, H))
        try:
            for i in range(frames):
                self.autoplay()
                self.tick()
                self.draw(canvas)
                raw = pygame.image.tostring(canvas, "RGB")
                proc.stdin.write(raw)
                if i % 30 == 0:
                    print(f"frame {i}/{frames}")
            proc.stdin.close()
            err = proc.stderr.read().decode("utf-8", "ignore")
            rc = proc.wait()
            if rc != 0:
                raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1200:]}")
            print("wrote", OUT)
        finally:
            pygame.quit()

def main():
    g = Game()
    if PLAY and not RECORD:
        g.play_interactive()
    else:
        g.record()

if __name__ == "__main__":
    main()
