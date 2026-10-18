import os
import re
import math
import random
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from youtubesearchpython.__future__ import VideosSearch
from SHIVMUSIC import app

W, H = 1920, 1080

# Red Wine palette (inspired by the reference but intentionally different)
WINE = (196, 30, 72)
ROSE = (255, 92, 130)
GOLD = (255, 196, 92)
CREAM = (255, 238, 225)
MUTED = (214, 186, 192)


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def glow_text(base, pos, text, font, fill, glow, radius=10, strength=3, anchor="la"):
    """Draw text with a soft neon glow."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text(pos, text, font=font, fill=glow, anchor=anchor)
    blurred = layer.filter(ImageFilter.GaussianBlur(radius))
    for _ in range(strength):
        base.alpha_composite(blurred)
    ImageDraw.Draw(base).text(pos, text, font=font, fill=fill, anchor=anchor)


def glow_shape(base, draw_fn, color, radius=18, strength=2):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer), color)
    blurred = layer.filter(ImageFilter.GaussianBlur(radius))
    for _ in range(strength):
        base.alpha_composite(blurred)
    base.alpha_composite(layer)


async def download_user_photo(user_id):
    try:
        async for photo in app.get_chat_photos(user_id, limit=1):
            return await app.download_media(photo.file_id, file_name=f"cache/{user_id}.jpg")
    except Exception:
        return None
    return None


def build_thumb(bg, avatar_img, title, channel, views, duration, seed):
    # --- Background: blurred cover + wine tint + vignette ---
    canvas = ImageOps.fit(bg.convert("RGB"), (W, H)).convert("RGBA")
    canvas = canvas.filter(ImageFilter.GaussianBlur(22))
    canvas.alpha_composite(Image.new("RGBA", (W, H), (22, 4, 12, 150)))
    vign = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vign).ellipse((-300, -250, W + 300, H + 250), fill=255)
    vign = vign.filter(ImageFilter.GaussianBlur(160))
    dark = Image.new("RGBA", (W, H), (8, 0, 4, 235))
    dark.putalpha(Image.eval(vign, lambda v: 255 - v))
    canvas.alpha_composite(dark)
    # soft wine light leaks
    leak = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(leak)
    ld.ellipse((-200, 650, 700, 1300), fill=(*WINE, 90))
    ld.ellipse((1300, -250, 2200, 450), fill=(*GOLD, 45))
    canvas.alpha_composite(leak.filter(ImageFilter.GaussianBlur(140)))

    f_brand = _font("SHIVMUSIC/assets/font.ttf", 64)
    f_vibe = _font("SHIVMUSIC/assets/font.ttf", 92)
    f_title = _font("SHIVMUSIC/assets/font.ttf", 66)
    f_meta = _font("SHIVMUSIC/assets/font2.ttf", 34)
    f_small = _font("SHIVMUSIC/assets/font2.ttf", 28)
    f_foot = _font("SHIVMUSIC/assets/font.ttf", 44)

    # --- Left: tilted YouTube cover card ---
    cw, ch = 560, 430
    cover = ImageOps.fit(bg.convert("RGB"), (cw, ch), centering=(0.5, 0.5)).convert("RGBA")
    pad = 70
    card = Image.new("RGBA", (cw + pad * 2, ch + pad * 2), (0, 0, 0, 0))
    gl = Image.new("RGBA", card.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    gd.rounded_rectangle((pad - 14, pad - 14, pad + cw + 14, pad + ch + 14), 52, fill=(*ROSE, 200))
    gl = gl.filter(ImageFilter.GaussianBlur(24))
    card.alpha_composite(gl)
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle((pad - 8, pad - 8, pad + cw + 8, pad + ch + 8), 46, fill=(*GOLD, 255))
    cd.rounded_rectangle((pad - 3, pad - 3, pad + cw + 3, pad + ch + 3), 42, fill=(*WINE, 255))
    m = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, cw - 1, ch - 1), 40, fill=255)
    card.paste(cover, (pad, pad), m)
    # glossy diagonal shine on the cover
    shine = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(shine).polygon(
        [(pad, pad), (pad + 220, pad), (pad + 60, pad + ch), (pad - 160, pad + ch)], fill=(255, 255, 255, 28))
    sm = Image.new("L", card.size, 0)
    ImageDraw.Draw(sm).rounded_rectangle((pad, pad, pad + cw, pad + ch), 40, fill=255)
    card.paste(Image.alpha_composite(card, shine), (0, 0), sm)
    card = card.rotate(6, resample=Image.BICUBIC, expand=True)
    canvas.alpha_composite(card, (40, 20))

    # --- Right: user avatar (slightly smaller) ---
    av = 300
    cx, cy = 1560, 330
    glow_shape(canvas, lambda d, c: d.ellipse((cx - av // 2 - 22, cy - av // 2 - 22,
                                              cx + av // 2 + 22, cy + av // 2 + 22), outline=c, width=14),
               (*ROSE, 255), radius=22, strength=2)
    d = ImageDraw.Draw(canvas)
    d.ellipse((cx - av // 2 - 10, cy - av // 2 - 10, cx + av // 2 + 10, cy + av // 2 + 10), outline=GOLD, width=5)
    if avatar_img is not None:
        a = ImageOps.fit(avatar_img.convert("RGB"), (av, av)).convert("RGBA")
    else:
        a = ImageOps.fit(bg.convert("RGB"), (av, av)).convert("RGBA").filter(ImageFilter.GaussianBlur(6))
    am = Image.new("L", (av, av), 0)
    ImageDraw.Draw(am).ellipse((0, 0, av - 1, av - 1), fill=255)
    canvas.paste(a, (cx - av // 2, cy - av // 2), am)
    # small music badge
    bx, by = cx + 112, cy + 108
    d.ellipse((bx - 36, by - 36, bx + 36, by + 36), fill=(30, 6, 14), outline=GOLD, width=4)
    d.ellipse((bx - 16, by + 4, bx - 2, by + 18), fill=GOLD)
    d.line((bx - 3, by + 10, bx - 3, by - 18), fill=GOLD, width=4)
    d.line((bx - 3, by - 18, bx + 14, by - 10), fill=GOLD, width=4)

    # --- Glowing labels ---
    glow_text(canvas, (1860, 50), "RED WINE", f_brand, CREAM, (*ROSE, 255), radius=14, strength=4, anchor="ra")
    glow_text(canvas, (1110, 170), "VIBE", f_vibe, GOLD, (*GOLD, 230), radius=18, strength=4, anchor="la")

    # --- Bottom glass player card ---
    x0, y0, x1, y1 = 70, 660, 1850, 960
    glow_shape(canvas, lambda d, c: d.rounded_rectangle((x0, y0, x1, y1), 44, outline=c, width=6),
               (*WINE, 255), radius=20, strength=2)
    glass = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glass).rounded_rectangle((x0, y0, x1, y1), 44, fill=(18, 4, 10, 205))
    canvas.alpha_composite(glass)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((x0, y0, x1, y1), 44, outline=(*GOLD, 170), width=2)
    d.line((x0 + 60, y0 + 2, x1 - 60, y0 + 2), fill=(255, 230, 210, 120), width=2)

    glow_text(canvas, (x0 + 10, y0 - 46), "NOW PLAYING", f_small, MUTED, (*ROSE, 160), radius=8, strength=1)

    # mic icon box
    ix, iy = x0 + 50, y0 + 50
    d.rounded_rectangle((ix, iy, ix + 120, iy + 120), 26, fill=(40, 8, 20), outline=(*ROSE, 200), width=3)
    d.rounded_rectangle((ix + 46, iy + 24, ix + 74, iy + 70), 14, outline=CREAM, width=4)
    d.arc((ix + 34, iy + 44, ix + 86, iy + 88), 0, 180, fill=CREAM, width=4)
    d.line((ix + 60, iy + 88, ix + 60, iy + 100), fill=CREAM, width=4)

    tx = ix + 160
    d.text((tx, y0 + 34), f"{channel[:28]}  |  {views} views", font=f_small, fill=MUTED)
    t = title
    while d.textlength(t, font=f_title) > 980 and len(t) > 4:
        t = t[:-4].rstrip() + "..."
    d.text((tx, y0 + 76), t, font=f_title, fill=CREAM)
    d.rounded_rectangle((tx, y0 + 170, tx + 230, y0 + 212), 21, fill=WINE)
    d.text((tx + 115, y0 + 191), "YouTube Music", font=f_small, fill=CREAM, anchor="mm")

    # waveform
    rng = random.Random(str(seed))
    wx, wy = 1330, y0 + 115
    bars = 38
    def draw_wave(dd, c):
        for i in range(bars):
            env = math.sin(math.pi * i / (bars - 1)) ** 0.8
            h = max(6, int(rng_vals[i] * env))
            x = wx + i * 12
            dd.rounded_rectangle((x, wy - h, x + 5, wy + h), 3, fill=c)
    rng_vals = [rng.randint(18, 78) for _ in range(bars)]
    glow_shape(canvas, draw_wave, (*GOLD, 255), radius=8, strength=1)

    # progress bar
    d = ImageDraw.Draw(canvas)
    py = y1 - 52
    px0, px1 = x0 + 60, x1 - 60
    d.line((px0, py, px1, py), fill=(110, 70, 80), width=4)
    prog = px0 + int((px1 - px0) * 0.08)
    glow_shape(canvas, lambda dd, c: dd.line((px0, py, prog, py), fill=c, width=6), (*ROSE, 255), radius=6, strength=1)
    d = ImageDraw.Draw(canvas)
    d.ellipse((prog - 11, py - 11, prog + 11, py + 11), fill=CREAM, outline=ROSE, width=3)
    d.text((px0, py + 14), "00:00", font=f_small, fill=MUTED)
    d.text((px1, py + 14), duration, font=f_small, fill=MUTED, anchor="ra")

    # --- Footer branding ---
    glow_text(canvas, (80, 1000), "BETA BOT HUB", f_foot, CREAM, (*ROSE, 255), radius=10)
    glow_text(canvas, (1840, 1000), "THE SHIV", f_foot, GOLD, (*GOLD, 220), radius=10, anchor="ra")
    return canvas.convert("RGB")


async def get_thumb(videoid, user_id, user_name):
    os.makedirs("cache", exist_ok=True)
    safe_videoid = re.sub(r"[^a-zA-Z0-9_-]", "_", str(videoid))[:80] or "track"
    final_path = f"cache/{safe_videoid}_{user_id}_v5.png"
    if os.path.exists(final_path):
        return final_path
    temp_path = f"cache/temp_{safe_videoid}_{user_id}.jpg"
    u_photo = None
    try:
        results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
        data = await results.next()
        lst = data.get("result", []) if isinstance(data, dict) else []
        result = lst[0] if lst else {}
        raw_title = result.get("title") or "Unknown Title"
        title = re.sub(r"\s+", " ", re.sub(r"[^\w\s|&'-]", " ", str(raw_title))).strip() or "Unknown Title"
        duration = str(result.get("duration") or "00:00")
        views = str((result.get("viewCount") or {}).get("short") or "Unknown").replace(" views", "")
        channel = str((result.get("channel") or {}).get("name") or "Unknown Artist")

        try:
            if result.get("thumbnails"):
                url = result["thumbnails"][0]["url"].split("?")[0]
                async with aiohttp.ClientSession() as s:
                    async with s.get(url) as r:
                        if r.status == 200:
                            async with aiofiles.open(temp_path, "wb") as f:
                                await f.write(await r.read())
        except Exception as e:
            print(f"Thumbnail download failed: {e}")

        try:
            bg = Image.open(temp_path).convert("RGBA") if os.path.exists(temp_path) and os.path.getsize(temp_path) else None
        except Exception:
            bg = None
        if bg is None:
            bg = Image.new("RGBA", (1280, 720), (60, 10, 25, 255))

        avatar = None
        u_photo = await download_user_photo(user_id)
        if u_photo and os.path.exists(u_photo):
            try:
                avatar = Image.open(u_photo)
            except Exception:
                avatar = None

        build_thumb(bg, avatar, title, channel, views, duration, videoid).save(final_path, "PNG")
        return final_path
    except Exception as e:
        print(f"Thumbnail General Error: {e}")
        return None
    finally:
        for p in (temp_path, u_photo):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
