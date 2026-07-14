"""
Lingexa Across - British vs American English
"""

import os, sys, json, random, asyncio, subprocess, urllib.request
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")
AI_MODEL = os.getenv("AI_MODEL")
if not AI_MODEL:
    raise ValueError("AI_MODEL not set!")

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
VIDEO_DIR = OUTPUT_DIR / "video"
HISTORY_DIR = OUTPUT_DIR / "history"
for d in [OUTPUT_DIR, VIDEO_DIR, HISTORY_DIR]:
    d.mkdir(exist_ok=True)

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30
BRITISH_VOICE = "en-GB-RyanNeural"
AMERICAN_VOICE = "en-US-GuyNeural"
CHANNEL_NAME = "Lingexa Across"
WORDS_PER_VIDEO = 3
PAIR_HISTORY_FILE = HISTORY_DIR / "all_generated_pairs.json"
FONTS_DIR = Path(__file__).parent / "fonts"
FLAGS_DIR = FONTS_DIR / "flags"

def ensure_flags():
    FLAGS_DIR.mkdir(parents=True, exist_ok=True)
    flags = {
        "uk.png": "https://flagcdn.com/48x36/gb.png",
        "us.png": "https://flagcdn.com/48x36/us.png",
    }
    for name, url in flags.items():
        path = FLAGS_DIR / name
        if not path.exists() or path.stat().st_size < 100:
            try:
                print(f"[flag] Downloading {name}...")
                urllib.request.urlretrieve(url, str(path))
                if path.exists() and path.stat().st_size > 100:
                    print(f"[flag] Downloaded {name}")
            except Exception as e:
                print(f"[flag] Failed to download {name}: {e}")
    return FLAGS_DIR

def load_pair_history():
    if PAIR_HISTORY_FILE.exists():
        with open(PAIR_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"pairs": [], "last_updated": None}

def save_pair_history(data):
    data["last_updated"] = datetime.now().isoformat()
    with open(PAIR_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_pair_used(brit_word, us_word):
    history = load_pair_history()
    for p in history.get("pairs", []):
        if p["british"].lower().strip() == brit_word.lower().strip() and p["american"].lower().strip() == us_word.lower().strip():
            return True
    return False

def add_pairs_to_history(pairs):
    history = load_pair_history()
    for p in pairs:
        history["pairs"].append({"british": p["british"], "american": p["american"], "category": p.get("category", ""), "generated_at": datetime.now().isoformat()})
    save_pair_history(history)

def generate_pair_data(num_pairs=WORDS_PER_VIDEO):
    max_attempts = 20
    categories = ["food and drink", "clothing", "transport", "housing", "workplace", "school", "shopping", "sports", "health", "technology"]
    collected = []
    for attempt in range(max_attempts):
        try:
            import requests
            url = "https://gen.pollinations.ai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {POLLINATIONS_API_KEY}", "Content-Type": "application/json"}
            cat = categories[attempt % len(categories)]
            remaining = num_pairs - len(collected)
            print(f"[api] Attempt {attempt + 1}: {cat} (need {remaining} more)")
            history = load_pair_history()
            used = []
            for p in history.get("pairs", [])[-30:]:
                used.append(f"{p['british']}/{p['american']}")
            used.extend([f"{c['british']}/{c['american']}" for c in collected])
            used_str = ", ".join(used) if used else "(none)"
            prompt = f"""Generate exactly 20 British vs American English word pairs from {cat}.

CRITICAL RULES:
- Each pair MUST have DIFFERENT words on each side (e.g. flat/apartment, not same word)
- NEVER repeat: {used_str}
- Both words must be SINGLE words each
- KEEP SHORT: definition max 8 words

Examples of GOOD pairs: lift/elevator, flat/apartment, chips/fries, boot/trunk, lorry/truck, queue/line, biscuit/cookie, jumper/sweater, trainer/sneaker, nappy/diaper, crisps/chips

Return JSON array. Each item:
[{{"british":"flat","american":"apartment","part_of_speech":"noun","definition":"a set of rooms","british_example":"She lives in a flat.","american_example":"He rents an apartment."}}]

Return ONLY the JSON array. No explanations."""
            payload = {"model": AI_MODEL, "messages": [{"role": "system", "content": "Return ONLY valid JSON arrays."}, {"role": "user", "content": prompt}], "temperature": 1.2}
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            pairs = json.loads(content)
            if not isinstance(pairs, list):
                raise ValueError("Not a list")
            fresh = []
            for p in pairs:
                b = p.get("british", "").strip()
                u = p.get("american", "").strip()
                if not b or not u:
                    continue
                if len(b.split()) > 1 or len(u.split()) > 1:
                    continue
                if is_pair_used(b, u):
                    continue
                if b.lower() == u.lower():
                    continue
                p["category"] = cat
                fresh.append(p)
                if len(collected) + len(fresh) >= num_pairs:
                    break
            collected.extend(fresh)
            if len(collected) >= num_pairs:
                add_pairs_to_history(collected[:num_pairs])
                return collected[:num_pairs]
        except Exception as e:
            print(f"[api] Attempt {attempt + 1} FAILED: {e}")
    if collected:
        add_pairs_to_history(collected)
        return collected
    raise RuntimeError("API failed all attempts")

def create_background():
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(VIDEO_HEIGHT):
        ratio = y / VIDEO_HEIGHT
        if ratio < 0.5:
            r, g, b = 248, 248, 252
        else:
            r = int(248 + (242 - 248) * ((ratio - 0.5) * 2))
            g = int(248 + (242 - 248) * ((ratio - 0.5) * 2))
            b = int(252 + (248 - 252) * ((ratio - 0.5) * 2))
        draw.rectangle([(0, y), (VIDEO_WIDTH, y + 1)], fill=(r, g, b))
    return img

async def gen_audio(text, voice, path):
    try:
        import edge_tts
        await edge_tts.Communicate(text, voice).save(path)
        return True
    except:
        return False

async def gen_audio_retry(text, voice, path, retries=3):
    for a in range(1, retries + 1):
        ok = await gen_audio(text, voice, path)
        if ok and Path(path).exists() and Path(path).stat().st_size > 100:
            return True
        await asyncio.sleep(2 * a)
    return False

def get_audio_duration(file):
    if not Path(file).exists():
        return 2.0
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except:
        return 2.0

def generate_all_audio(pairs, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_files = []
    total = 0.0
    for i, p in enumerate(pairs):
        bf = out_dir / f"b_{i}.mp3"
        uf = out_dir / f"u_{i}.mp3"
        cf = out_dir / f"p_{i}.mp3"
        bt = f"British: {p['british']}. {p['definition']}. Example: {p.get('british_example', '')}."
        ut = f"American: {p['american']}. Example: {p.get('american_example', '')}."
        ff = p.get("fun_fact", "")
        if ff:
            bt += f" {ff}"
        asyncio.run(gen_audio_retry(bt, BRITISH_VOICE, str(bf)))
        asyncio.run(gen_audio_retry(ut, AMERICAN_VOICE, str(uf)))
        for f in [bf, uf]:
            if not (f.exists() and f.stat().st_size > 100):
                subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3", str(f)], capture_output=True)
        cl = out_dir / f"cl_{i}.txt"
        with open(cl, "w") as f:
            f.write(f"file '{bf.as_posix()}'\nfile '{uf.as_posix()}'\n")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(cl), "-c:a", "libmp3lame", str(cf)], capture_output=True)
        if cl.exists():
            cl.unlink()
        dur = get_audio_duration(str(cf))
        audio_files.append({"file": str(cf), "duration": dur})
        total += dur + 0.3
    print(f"[audio] {len(audio_files)} pairs, {total:.1f}s")
    return audio_files, total

def create_final_audio(audio_files, out_file):
    od = Path(out_file).parent
    parts = []
    for i, af in enumerate(audio_files):
        p = od / f"pd_{i}.mp3"
        subprocess.run(["ffmpeg", "-y", "-i", str(af["file"]), "-af", "apad=pad_dur=0.3", "-ar", "24000", "-ac", "1", "-c:a", "libmp3lame", str(p)], capture_output=True)
        parts.append(p)
    cl = od / "cl.txt"
    with open(cl, "w") as f:
        for part in parts:
            f.write(f"file '{str(part.resolve()).replace(chr(92), chr(47))}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(cl), "-c:a", "libmp3lame", str(out_file)], capture_output=True)
    for p in parts:
        if p.exists(): p.unlink()
    if cl.exists(): cl.unlink()
    return Path(out_file).exists() and Path(out_file).stat().st_size > 100

def wrap_text(draw, text, font, max_w):
    words = text.split()
    lines = []
    cur = []
    for w in words:
        t = ' '.join(cur + [w])
        if draw.textbbox((0, 0), t, font=font)[2] <= max_w or not cur:
            cur.append(w)
        else:
            lines.append(' '.join(cur))
            cur = [w]
    if cur:
        lines.append(' '.join(cur))
    return lines

def generate_pair_image(pair, bg_image, out_path):
    from PIL import Image, ImageDraw, ImageFont

    img = bg_image.copy().convert('RGBA')
    draw = ImageDraw.Draw(img)

    MX = 90
    CX = VIDEO_WIDTH // 2
    CW = VIDEO_WIDTH - MX * 2

    FONT_BOLD = [
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf","/usr/share/fonts/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf","/usr/share/fonts/Liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf","C:/Windows/Fonts/verdanab.ttf","C:/Windows/Fonts/segoeuib.ttf",
    ]
    FONT_REG = [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf","/usr/share/fonts/noto/NotoSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf","C:/Windows/Fonts/verdana.ttf","C:/Windows/Fonts/segoeui.ttf",
    ]

    def lf(paths, sz):
        for p in paths:
            try:
                f = ImageFont.truetype(p, sz)
                if draw.textbbox((0, 0), "AW", font=f)[2] > sz * 0.5:
                    return f
            except:
                continue
        return ImageFont.load_default()

    f_head = lf(FONT_BOLD, 65)
    f_tag = lf(FONT_BOLD, 42)
    f_word = lf(FONT_BOLD, 80)
    f_flag = lf(FONT_BOLD, 36)
    f_vs = lf(FONT_BOLD, 44)
    f_pos = lf(FONT_BOLD, 50)
    f_dlab = lf(FONT_BOLD, 42)
    f_def = lf(FONT_REG, 60)
    f_exlab = lf(FONT_BOLD, 42)
    f_ex = lf(FONT_REG, 48)
    f_foot = lf(FONT_BOLD, 42)

    brit = pair.get("british", "").upper()
    us = pair.get("american", "").upper()
    definition = pair.get("definition", "a word difference between UK and US English")
    brit_ex = pair.get("british_example", "")
    us_ex = pair.get("american_example", "")
    pos = pair.get("part_of_speech", "")

    H = (45, 35, 65)
    W = (25, 20, 45)
    DB = (65, 50, 95)
    EB = (95, 80, 125)
    L = (80, 65, 105)

    draw.rectangle([(0, 0), (VIDEO_WIDTH, 150)], fill=H)
    draw.text((CX, 50), CHANNEL_NAME.upper(), fill=(255, 255, 255), font=f_head, anchor="mm")
    draw.text((CX, 120), "BRITISH ENGLISH  vs  AMERICAN ENGLISH", fill=(200, 195, 215), font=lf(FONT_REG, 34), anchor="mm")

    y = 340

    fl_dir = ensure_flags()
    try:
        fl_uk = Image.open(FLAGS_DIR / "uk.png").convert('RGBA').resize((48, 36), Image.LANCZOS)
    except:
        fl_uk = None
    try:
        fl_us = Image.open(FLAGS_DIR / "us.png").convert('RGBA').resize((48, 36), Image.LANCZOS)
    except:
        fl_us = None

    if fl_uk:
        img.paste(fl_uk, (CX - 90 - 24, y - 18), fl_uk)
    draw.text((CX + 40, y), "BRITISH", fill=(55, 65, 145), font=f_flag, anchor="mm")
    y += 55

    MAX_WW = CW
    wfs = 80
    wf = lf(FONT_BOLD, wfs)
    ww = draw.textbbox((0, 0), brit, font=wf)[2]
    while ww > MAX_WW and wfs > 30:
        wfs -= 5
        wf = lf(FONT_BOLD, wfs)
        ww = draw.textbbox((0, 0), brit, font=wf)[2]
    wh = draw.textbbox((0, 0), "Ay", font=wf)[3] - draw.textbbox((0, 0), "Ay", font=wf)[1]
    draw.text((CX, y + wh // 2), brit, fill=(40, 40, 100), font=wf, anchor="mm", stroke_width=2, stroke_fill=(210, 205, 220))
    y += wh + 70

    vs_y = y
    vs_b = draw.textbbox((0, 0), "VS", font=f_vs)
    vs_w = vs_b[2] - vs_b[0]
    vs_h = vs_b[3] - vs_b[1]
    draw.rounded_rectangle([(CX - vs_w // 2 - 20, vs_y - 12), (CX + vs_w // 2 + 20, vs_y + vs_h + 16)], radius=14, fill=(90, 80, 110))
    draw.text((CX, vs_y + vs_h // 2), "VS", fill=(255, 255, 255), font=f_vs, anchor="mm")
    y = vs_y + vs_h + 70

    # American label + word
    if fl_us:
        img.paste(fl_us, (CX - 90 - 24, y - 18), fl_us)
    draw.text((CX + 40, y), "AMERICAN", fill=(150, 35, 35), font=f_flag, anchor="mm")
    y += 50

    wfs2 = 80
    wf2 = lf(FONT_BOLD, wfs2)
    ww2 = draw.textbbox((0, 0), us, font=wf2)[2]
    while ww2 > MAX_WW and wfs2 > 30:
        wfs2 -= 5
        wf2 = lf(FONT_BOLD, wfs2)
        ww2 = draw.textbbox((0, 0), us, font=wf2)[2]
    wh2 = draw.textbbox((0, 0), "Ay", font=wf2)[3] - draw.textbbox((0, 0), "Ay", font=wf2)[1]
    draw.text((CX, y + wh2 // 2), us, fill=(140, 20, 20), font=wf2, anchor="mm", stroke_width=2, stroke_fill=(225, 200, 200))
    y += wh2 + 70

    # POS
    if pos:
        pb = draw.textbbox((0, 0), pos.upper(), font=f_pos)
        pw = pb[2] - pb[0]
        ph = pb[3] - pb[1]
        draw.rounded_rectangle([(CX - pw // 2 - 16, y), (CX + pw // 2 + 16, y + ph + 18)], radius=10, fill=(75, 55, 115))
        draw.text((CX, y + ph // 2 + 9), pos.upper(), fill=(255, 245, 140), font=f_pos, anchor="mm")
        y += ph + 70

    # MEANING
    draw.text((MX, y), "MEANING", fill=L, font=f_dlab, anchor="lm")
    y += 60

    dl = wrap_text(draw, definition, f_def, CW - 60)
    while len(dl) > 2 and f_def.size > 36:
        f_def = lf(FONT_REG, f_def.size - 4)
        dl = wrap_text(draw, definition, f_def, CW - 60)
    lh = draw.textbbox((0, 0), "A", font=f_def)[3] - draw.textbbox((0, 0), "A", font=f_def)[1]
    ls = int(lh * 1.5)
    th = (len(dl) - 1) * ls + lh
    pd = 40
    bh = th + pd * 2
    box = Image.new('RGBA', (CW, bh), DB + (255,))
    bd = ImageDraw.Draw(box)
    bd.rounded_rectangle([(0, 0), (CW, bh)], radius=16, fill=DB + (255,))
    for i, line in enumerate(dl):
        ly = pd + (i * ls) + (lh // 2)
        bd.text((CW // 2, ly), line, fill=(255, 255, 255), font=f_def, anchor="mm")
    img.paste(box, (MX, y), box)
    y += bh + 65

    # EXAMPLES
    if brit_ex or us_ex:
        draw.text((MX, y), "EXAMPLES", fill=L, font=f_exlab, anchor="lm")
        y += 60
        if brit_ex:
            ef = lf(FONT_REG, 42)
            el = wrap_text(draw, f"UK: {brit_ex}", ef, CW - 50)
            while len(el) > 2 and ef.size > 28:
                ef = lf(FONT_REG, ef.size - 4)
                el = wrap_text(draw, f"UK: {brit_ex}", ef, CW - 50)
            tlh = draw.textbbox((0, 0), "A", font=ef)[3] - draw.textbbox((0, 0), "A", font=ef)[1]
            tls = int(tlh * 2.0)
            tth = (len(el) - 1) * tls + tlh + 28
            ebox = Image.new('RGBA', (CW, tth), (220, 215, 230, 200))
            ed = ImageDraw.Draw(ebox)
            ed.rounded_rectangle([(0, 0), (CW, tth)], radius=12, fill=(220, 215, 230, 200))
            for i, line in enumerate(el):
                ed.text((20, 14 + (i * tls) + tlh // 2), line, fill=(40, 35, 70), font=ef, anchor="lm")
            img.paste(ebox, (MX, y), ebox)
            y += tth + 15
        if us_ex:
            ef2 = lf(FONT_REG, 42)
            el2 = wrap_text(draw, f"US: {us_ex}", ef2, CW - 50)
            while len(el2) > 2 and ef2.size > 28:
                ef2 = lf(FONT_REG, ef2.size - 4)
                el2 = wrap_text(draw, f"US: {us_ex}", ef2, CW - 50)
            tlh2 = draw.textbbox((0, 0), "A", font=ef2)[3] - draw.textbbox((0, 0), "A", font=ef2)[1]
            tls2 = int(tlh2 * 2.0)
            tth2 = (len(el2) - 1) * tls2 + tlh2 + 28
            ebox2 = Image.new('RGBA', (CW, tth2), (235, 210, 210, 200))
            ed2 = ImageDraw.Draw(ebox2)
            ed2.rounded_rectangle([(0, 0), (CW, tth2)], radius=12, fill=(235, 210, 210, 200))
            for i, line in enumerate(el2):
                ed2.text((20, 14 + (i * tls2) + tlh2 // 2), line, fill=(80, 20, 20), font=ef2, anchor="lm")
            img.paste(ebox2, (MX, y), ebox2)
            y += tth2 + 15

    draw.rectangle([(0, VIDEO_HEIGHT - 65), (VIDEO_WIDTH, VIDEO_HEIGHT)], fill=H)
    draw.text((CX, VIDEO_HEIGHT - 32), f"UK vs US Daily  |  {CHANNEL_NAME}", fill=(210, 200, 220), font=f_foot, anchor="mm")

    img = img.convert('RGB')
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=96, optimize=True)
    print(f"[image] {Path(out_path).name}")
    return out_path

def create_video(image_files, audio_files, out_file):
    print(f"[video] {len(image_files)} images...")
    clips = []
    for i, (ip, ai) in enumerate(zip(image_files, audio_files)):
        tc = Path(out_file).parent / f"c_{i}.mp4"
        d = ai["duration"]
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(ip), "-i", str(ai["file"]),
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,fps={FPS}",
            "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            "-t", f"{d}", "-shortest", str(tc)], capture_output=True)
        ad = get_audio_duration(str(tc))
        print(f"  Clip {i+1}: {ad:.1f}s")
        clips.append(tc)
    if not clips:
        return False
    cf = Path(out_file).parent / "cl.txt"
    with open(cf, "w") as f:
        for c in clips:
            f.write(f"file '{str(c.resolve()).replace(chr(92), chr(47))}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(cf), "-c", "copy", str(out_file)], capture_output=True)
    for c in clips:
        if c.exists(): c.unlink()
    if cf.exists(): cf.unlink()
    print(f"[video] {Path(out_file).name}")
    return True

def generate_reel():
    print(f"\n{'='*80}\n  {CHANNEL_NAME.upper()}\n{'='*80}\n")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rd = VIDEO_DIR / f"pairs_{ts}"
    rd.mkdir()
    print("[1/3] Generating word pairs...")
    pairs = generate_pair_data(WORDS_PER_VIDEO)
    for i, p in enumerate(pairs, 1):
        print(f"  {i}. {p['british']}  vs  {p['american']}")
    print("\n[2/3] Generating images...")
    bg = create_background()
    imgs = []
    for i, p in enumerate(pairs):
        ip = rd / f"p_{i}.jpg"
        generate_pair_image(p, bg, str(ip))
        imgs.append(str(ip))
    print("\n[3/3] Generating audio & video...")
    af, td = generate_all_audio(pairs, str(rd))
    fa = rd / "narration.mp3"
    create_final_audio(af, str(fa))
    ov = rd / "final_reel.mp4"
    create_video(imgs, af, str(ov))
    meta = {"channel": CHANNEL_NAME, "pairs": pairs, "timestamp": ts, "video": str(ov), "duration": td}
    with open(rd / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"\n{'='*80}\n  COMPLETE! {td:.1f}s\n{'='*80}\n")
    return meta

if __name__ == "__main__":
    print(f"\n{'='*80}\n  {CHANNEL_NAME.upper()}\n{'='*80}\n")
    generate_reel()
