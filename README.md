# Sparkle Portrait ✨

Turns any photo into animated sparkle line art. Particles fly in and trace the photo's outlines in pastel colours, then a quote fades in.

Built with Python, OpenCV (edge detection) and Pygame (animation).

## How it works

1. The photo is resized, converted to grayscale and lightly blurred.
2. OpenCV's Canny edge detector keeps only the outlines.
3. Every outline pixel becomes a target for a particle.
4. Particles fly in on curved paths, roughly top to bottom, and settle into the drawing.
5. The quote fades in and the finished piece twinkles.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python sparkle_portrait.py photo.jpg
python sparkle_portrait.py photo.jpg --quote "Your quote here"
```

Press **R** to replay, **ESC** to quit.

## Record a video (for Reels / Shorts)

```bash
python sparkle_portrait.py photo.jpg --save reel.mp4
python sparkle_portrait.py photo.jpg --save reel.mp4 --headless   # no window, faster
```

## Options

| Option | Default | What it does |
|---|---|---|
| `--quote` | "Light And Shadow, Both Mine." | Text at the end |
| `--low` / `--high` | 65 / 150 | Edge sensitivity. Lower values give more lines |
| `--points` | 7000 | Max particles. Lower is faster |
| `--seed` | 42 | Same seed gives the same animation |
| `--save` | none | Save as .mp4 |
| `--headless` | off | Render without opening a window |

## Tips

- Photos with a plain background and clear lighting give the cleanest outlines.
- Too messy? Raise the thresholds: `--low 90 --high 200`.
- Too few lines? Lower them: `--low 30 --high 90`.

Inspired by the sparkle-portrait reels by coded.by.adri.
