"""
Sparkle Portrait
Turns any photo into animated sparkle line art with a fading quote.

Usage:
    python sparkle_portrait.py photo.jpg
    python sparkle_portrait.py photo.jpg --quote "Light And Shadow, Both Mine."
    python sparkle_portrait.py photo.jpg --save reel.mp4          # record a video
    python sparkle_portrait.py photo.jpg --save reel.mp4 --headless

Controls (live window):  R = replay   ESC / close = quit
"""
import argparse
import math
import os
import random
import sys

import cv2
import numpy as np

# ---------------------------------------------------------------- settings
W, H = 700, 800
BG = (8, 5, 15)
FPS = 60

WAIT = 1.5    # seconds before drawing starts
DRAW = 10.0   # seconds the outline takes to draw
TEXT = 3.0    # seconds for the quote to fade in
FINAL = 3.0   # seconds to hold the finished piece

COLORS = [
    (255, 165, 205),  # pink
    (205, 165, 255),  # lavender
    (145, 210, 255),  # sky blue
    (255, 215, 175),  # peach
    (255, 190, 225),  # rose
]
TEXT_COLOR = (240, 225, 245)
TEXT_AREA = 120   # px reserved at the bottom for the quote


# ---------------------------------------------------------------- helpers
def mix(c1, c2, amount):
    """Blend colour c1 towards c2 by amount (0..1)."""
    return tuple(int(a + (b - a) * amount) for a, b in zip(c1, c2))


def sparkle(surface, x, y, color, size):
    """Four-point twinkle: a bright cross plus a fainter diagonal cross."""
    import pygame
    x, y = int(x), int(y)
    pygame.draw.line(surface, color, (x - size, y), (x + size, y))
    pygame.draw.line(surface, color, (x, y - size), (x, y + size))
    d = max(1, size // 2)
    dim = mix(color, BG, 0.5)
    pygame.draw.line(surface, dim, (x - d, y - d), (x + d, y + d))
    pygame.draw.line(surface, dim, (x - d, y + d), (x + d, y - d))


def load_edge_points(path, low, high, max_points):
    """Photo -> outline pixels (screen coordinates) via Canny edge detection."""
    img = cv2.imread(path)
    if img is None:
        sys.exit(f"Could not read image: {path}")

    ih, iw = img.shape[:2]
    scale = min((W - 90) / iw, (H - TEXT_AREA - 40) / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(gray, low, high)

    ys, xs = np.where(edges > 0)
    if len(xs) == 0:
        sys.exit("No outlines found. Try lower thresholds, e.g. --low 30 --high 90")

    ox = (W - nw) // 2
    oy = (H - TEXT_AREA - nh) // 2 + 10
    pts = np.column_stack((xs + ox, ys + oy)).astype(np.float32)

    if len(pts) > max_points:  # thin out very busy photos
        keep = np.random.choice(len(pts), max_points, replace=False)
        pts = pts[keep]
    return pts


# ---------------------------------------------------------------- scene
class Scene:
    def __init__(self, targets, quote, font):
        import pygame
        self.pygame = pygame
        self.targets = targets
        self.quote = quote
        self.font = font
        self.reset()

    def reset(self):
        pg = self.pygame
        n = len(self.targets)
        self.n = n

        # Draw roughly top-to-bottom, with some randomness so it feels organic.
        key = self.targets[:, 1] + np.random.uniform(-60, 60, n)
        rank = np.empty(n)
        rank[np.argsort(key)] = np.arange(n)
        self.t0 = WAIT + rank / n * DRAW * 0.8
        self.dur = np.random.uniform(0.8, 1.6, n)

        # Each particle flies in from a random direction on a gentle curve.
        ang = np.random.uniform(0, 2 * np.pi, n)
        dist = np.random.uniform(120, 380, n)
        self.starts = self.targets + np.column_stack((np.cos(ang), np.sin(ang))) * dist[:, None]
        delta = self.targets - self.starts
        length = np.linalg.norm(delta, axis=1, keepdims=True) + 1e-6
        self.perp = np.column_stack((-delta[:, 1], delta[:, 0])) / length
        self.curve = np.random.uniform(-60, 60, n)

        self.col = np.random.randint(0, len(COLORS), n)
        self.size = np.random.choice([1, 1, 2], n)
        self.landed = np.zeros(n, bool)
        self.art = pg.Surface((W, H), pg.SRCALPHA)

        self.text = self.font.render(self.quote, True, TEXT_COLOR)
        self.stars = [
            (random.uniform(0, W), random.uniform(0, H),
             random.uniform(0, 2 * math.pi), random.uniform(1.0, 3.0),
             random.choice([1, 1, 1, 2, 3]))
            for _ in range(140)
        ]

    def draw(self, screen, t):
        pg = self.pygame
        screen.fill(BG)

        # 1. background stars, twinkling
        for x, y, phase, speed, size in self.stars:
            b = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(t * speed + phase))
            c = mix(BG, (210, 210, 240), b)
            if size == 1:
                screen.set_at((int(x), int(y)), c)
            else:
                sparkle(screen, x, y, c, size)

        # 2. particles that arrived this frame get baked into the artwork
        p = np.clip((t - self.t0) / self.dur, 0.0, 1.0)
        newly = (p >= 1.0) & ~self.landed
        for i in np.nonzero(newly)[0]:
            x, y = self.targets[i]
            pg.draw.circle(self.art, COLORS[self.col[i]], (int(x), int(y)), int(self.size[i]))
        self.landed |= newly
        screen.blit(self.art, (0, 0))

        # 3. particles still in flight
        active = np.nonzero((p > 0.0) & (p < 1.0))[0]
        if active.size:
            e = 1 - (1 - p[active]) ** 3  # ease-out
            pos = (self.starts[active]
                   + (self.targets[active] - self.starts[active]) * e[:, None]
                   + self.perp[active] * (self.curve[active] * np.sin(np.pi * e))[:, None])
            for k, i in enumerate(active):
                c = COLORS[self.col[i]]
                x, y = pos[k]
                pg.draw.circle(screen, mix(c, BG, 0.7), (int(x), int(y)), 3)  # soft halo
                pg.draw.circle(screen, c, (int(x), int(y)), 1)
                if random.random() < 0.02:
                    sparkle(screen, x, y, c, random.randint(3, 6))

        # 4. once drawing is done, random points along the outline twinkle
        if t > WAIT + DRAW:
            done = np.nonzero(self.landed)[0]
            for i in np.random.choice(done, min(20, done.size), replace=False):
                x, y = self.targets[i]
                sparkle(screen, x, y, COLORS[self.col[i]], random.randint(2, 5))

        # 5. quote fades in
        f = (t - (WAIT + DRAW)) / TEXT
        if f > 0:
            self.text.set_alpha(int(255 * min(1.0, f)))
            rect = self.text.get_rect(center=(W // 2, H - TEXT_AREA // 2 - 10))
            screen.blit(self.text, rect)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Turn a photo into animated sparkle line art.")
    ap.add_argument("image", help="path to the photo (jpg/png)")
    ap.add_argument("--quote", default="Light And Shadow, Both Mine.", help="text shown at the end")
    ap.add_argument("--title", default="Sparkle Portrait", help="window title")
    ap.add_argument("--low", type=int, default=65, help="Canny low threshold (lower = more lines)")
    ap.add_argument("--high", type=int, default=150, help="Canny high threshold")
    ap.add_argument("--points", type=int, default=7000, help="max sparkle points")
    ap.add_argument("--seed", type=int, default=42, help="random seed (same seed = same animation)")
    ap.add_argument("--save", metavar="OUT.mp4", help="record the animation to a video file")
    ap.add_argument("--headless", action="store_true", help="no window (use with --save)")
    args = ap.parse_args()

    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    import pygame

    random.seed(args.seed)
    np.random.seed(args.seed)

    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption(args.title)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("georgia", 34, italic=True)

    targets = load_edge_points(args.image, args.low, args.high, args.points)
    scene = Scene(targets, args.quote, font)

    writer = None
    if args.save:
        writer = cv2.VideoWriter(args.save, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    total_frames = int((WAIT + DRAW + TEXT + FINAL) * FPS)

    frame = 0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r and not writer:
                    scene.reset()
                    frame = 0

        t = frame / FPS  # frame-based time keeps recordings smooth
        scene.draw(screen, t)
        pygame.display.flip()

        if writer:
            rgb = pygame.surfarray.array3d(screen).transpose(1, 0, 2)
            writer.write(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
            if frame + 1 >= total_frames:
                running = False
        if not args.headless:
            clock.tick(FPS)
        frame += 1

    if writer:
        writer.release()
        print(f"Saved {args.save}")
    pygame.quit()


if __name__ == "__main__":
    main()
