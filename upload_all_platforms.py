"""
Lingexa Across - British vs American English Upload Script
"""

import os, sys, json, io
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

load_dotenv()
upload_dir = Path(__file__).parent / "upload"
if upload_dir.exists() and str(upload_dir) not in sys.path:
    sys.path.insert(0, str(upload_dir))

upload_to_facebook = None
upload_to_instagram = None
upload_to_youtube = None
try:
    from upload_facebook import upload_to_facebook as fb_upload; upload_to_facebook = fb_upload
except ImportError: pass
try:
    from upload_instagram import upload_to_instagram as ig_upload; upload_to_instagram = ig_upload
except ImportError: pass
try:
    from upload_to_youtube import upload_to_youtube as yt_upload; upload_to_youtube = yt_upload
except ImportError: pass

CHANNEL_NAME = "Lingexa Across"

def get_latest_reel():
    video_dir = Path("output/video")
    if not video_dir.exists():
        return None
    reels = list(video_dir.glob("*/final_reel.mp4"))
    if not reels:
        return None
    latest = max(reels, key=lambda p: p.stat().st_mtime)
    metadata_file = latest.parent / "metadata.json"
    metadata = {}
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    pairs_data = metadata.get("pairs", [])
    return {"video_path": str(latest), "metadata": metadata, "pairs": pairs_data, "word": pairs_data[0].get("british", "UK") if pairs_data else "UK"}

def generate_caption(reel_data, platform="facebook"):
    pairs = reel_data.get("pairs", [])
    if not pairs:
        return f"British vs American English with {CHANNEL_NAME}! #LingexaAcross #BritishVsAmerican"
    if platform == "facebook":
        lines = [f"🇬🇧 British vs 🇺🇸 American: 3 Word Differences!", f""]
        for i, p in enumerate(pairs, 1):
            brit = p.get("british", "")
            us = p.get("american", "")
            definition = p.get("definition", "")
            brit_ex = p.get("british_example", "")
            us_ex = p.get("american_example", "")
            lines.append(f"{i}. {brit.upper()} vs {us.upper()}")
            lines.append(f"   → {definition}")
            lines.append(f"   🇬🇧 {brit_ex}")
            lines.append(f"   🇺🇸 {us_ex}")
            lines.append(f"")
        lines.extend([f"💡 Save this to remember the difference!", f"🔔 Follow {CHANNEL_NAME} for daily UK vs US words!", f"", f"#LingexaAcross #BritishVsAmerican #UKvsUS #English #LearnEnglish #BritishEnglish #AmericanEnglish #LanguageLearning #ESL"])
    else:
        lines = [f"🇬🇧 vs 🇺🇸 British vs American words today!", f""]
        for i, p in enumerate(pairs[:3], 1):
            lines.append(f"{i}. {p['british']} / {p['american']}")
        lines.extend([f"", f"#LingexaAcross #BritishVsAmerican #English"])
    return "\n".join(lines)

def upload_to_all_platforms(video_path, caption, word, reel_data=None):
    results = {"timestamp": datetime.now().isoformat(), "word": word, "video": video_path, "uploads": {}, "platforms_attempted": [], "platforms_successful": [], "platforms_skipped": [], "platforms_failed": []}
    print(f"\n{'='*80}\n{CHANNEL_NAME.upper()} - MULTI-PLATFORM UPLOAD\n{'='*80}")
    if not Path(video_path).exists():
                # === UPLOAD STATUS REPORT ===
    print("\n" + "=" * 60)
    print("UPLOAD STATUS REPORT")
    print("=" * 60)
    uploads = results.get("uploads", {})
    for pname, pkey in [("INSTAGRAM", "instagram"), ("FACEBOOK", "facebook"), ("YOUTUBE", "youtube"),
                          ("THREADS", "threads"), ("TIKTOK", "tiktok"), ("TWITTER", "twitter"),
                          ("VK", "vk"), ("TELEGRAM", "telegram")]:
        pinfo = uploads.get(pkey, {})
        if pinfo and pinfo.get("status") == "success":
            pid = pinfo.get("id", "N/A")
            print(f"{pname}: SUCCESS (ID: {pid})")
        elif pinfo:
            err = str(pinfo.get("error", pinfo.get("reason", "unknown")))[:80]
            print(f"{pname}: FAILED - {err}")
        else:
            pl = pkey.lower()
            failed = pl in [p.lower() for p in results.get("platforms_failed", [])]
            skipped = pl in [p.lower() for p in results.get("platforms_skipped", [])]
            print(f"{pname}: {'FAILED' if failed else ('SKIPPED' if skipped else '-')}")
    print("=" * 60)

    return results
    platforms = [("facebook", upload_to_facebook, "Facebook"), ("instagram", upload_to_instagram, "Instagram"), ("youtube", upload_to_youtube, "YouTube")]
    for platform_name, upload_func, display_name in platforms:
        print(f"\n{display_name} UPLOAD...")
        results["platforms_attempted"].append(platform_name)
        if upload_func:
            try:
                if platform_name == "facebook":
                    upload_result = upload_func(video_path=video_path, description=caption, title=f"UK vs US: {word}")
                elif platform_name == "instagram":
                    upload_result = upload_func(video_path=video_path, caption=caption, is_story=False)
                elif platform_name == "youtube":
                    pairs = reel_data.get("pairs", [])
                    if pairs:
                        words = [p.get("british", "") for p in pairs]
                        words_str = ", ".join(words)
                        yt_title = f"UK vs US: {words_str} | British vs American English"
                        yt_description_lines = [
                            f"🇬🇧 vs 🇺🇸 British vs American English - {len(pairs)} Word Differences!",
                            "",
                        ]
                        for i, p in enumerate(pairs, 1):
                            b = p.get("british", "")
                            u = p.get("american", "")
                            d = p.get("definition", "")
                            be = p.get("british_example", "")
                            ue = p.get("american_example", "")
                            yt_description_lines.append(f"{i}. {b.upper()} vs {u.upper()}")
                            yt_description_lines.append(f"   {d}")
                            if be: yt_description_lines.append(f"   🇬🇧 {be}")
                            if ue: yt_description_lines.append(f"   🇺🇸 {ue}")
                            yt_description_lines.append("")
                        yt_description_lines.extend([
                            "Follow for daily UK vs US words!",
                            "",
                            "#BritishVsAmerican #UKvsUS #LearnEnglish #BritishEnglish #AmericanEnglish #Shorts",
                        ])
                        yt_description = "\n".join(yt_description_lines)
                        yt_tags = ["british vs american", "uk vs us", "learn english", "british english", "american english", "vocabulary", "english lesson"] + [w.lower() for w in words]
                    else:
                        yt_title = "UK vs US English | British vs American Words"
                        yt_description = "British vs American English word differences with Lingexa Across!"
                        yt_tags = ["british vs american", "uk vs us", "learn english"]
                    upload_result = upload_func(video_path=video_path, title=yt_title, description=yt_description, tags=yt_tags, category_id='27')
                if upload_result:
                    results["uploads"][platform_name] = upload_result
                    results["platforms_successful"].append(platform_name)
                else:
                    results["platforms_failed"].append(platform_name)
            except Exception as e:
                results["uploads"][platform_name] = {"status": "failed", "error": str(e)}
                results["platforms_failed"].append(platform_name)
        else:
            results["platforms_skipped"].append(platform_name)
    print(f"\nSuccessful: {len(results['platforms_successful'])}, Failed: {len(results['platforms_failed'])}, Skipped: {len(results['platforms_skipped'])}")
        # === UPLOAD STATUS REPORT ===
    print("\n" + "=" * 60)
    print("UPLOAD STATUS REPORT")
    print("=" * 60)
    success_list = [p.lower() for p in results.get("platforms_successful", [])]
    failed_list = [p.lower() for p in results.get("platforms_failed", [])]
    skipped_list = [p.lower() for p in results.get("platforms_skipped", [])]
    for pname in ["INSTAGRAM", "FACEBOOK", "YOUTUBE", "THREADS", "TIKTOK", "TWITTER", "VK", "TELEGRAM"]:
        pl = pname.lower()
        if pl in success_list: status = "SUCCESS"
        elif pl in failed_list: status = "FAILED"
        elif pl in skipped_list: status = "SKIPPED"
        else: status = "-"
        print(f"{pname}: {status}")
    print("=" * 60)
    return results

def main():
    reel = get_latest_reel()
    if not reel:
        print("No reel found! Run lingexa_across_bot.py first.")
        sys.exit(1)
    caption = generate_caption(reel, platform="facebook")
    print(f"Caption ({len(caption)} chars):")
    try:
        print(f"{caption[:300]}...")
    except UnicodeEncodeError:
        print(f"{caption[:300].encode('utf-8', errors='replace').decode('utf-8', errors='replace')}...")
    upload_to_all_platforms(reel['video_path'], caption, reel['word'], reel)

if __name__ == "__main__":
    main()
