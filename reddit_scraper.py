"""
Reddit Sentiment Scraper — Team 1 Prototype (v4)
Uses Reddit's public .json endpoint (no API credentials required)
Sentiment analysis via Ollama + gemma4:e4b-it-q4_0 running locally

CHANGES FROM v3:
  - Fixed DeprecationWarning: datetime.utcfromtimestamp replaced with
    timezone-aware datetime.fromtimestamp(..., tz=datetime.timezone.utc)
  - Ollama timeout increased from 60s → 120s (first two posts cold-start
    the model which can exceed 60s). Added 3-attempt retry with escalating
    timeouts (120s → 150s → 180s) so a slow start doesn't drop posts.

Requirements:
    pip install requests

Usage:
    1. Make sure Ollama is running: ollama run gemma4:e4b-it-q4_0
    2. Edit SUBREDDITS and KEYWORD below to match your client
    3. Run: python3 reddit_scraper.py
"""

import requests
import json
import time
import datetime

# ─────────────────────────────────────────────
#  CONFIGURATION — edit these for each client
# ─────────────────────────────────────────────

SUBREDDITS = [
    "Nike",
    "Sneakers",
    "running",
    "runninglifestyle",
    "beginnerrunning",
]
KEYWORD     = "Nike"
POST_LIMIT  = 25            # Posts per subreddit (5 subs × 25 = 125 total)
TOTAL_LIMIT = 125           # Hard cap across all subreddits combined
OUTPUT_FILE = "reddit_data.json"

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma4:e4b-it-q4_K_M"  # 4-bit quantization — faster, lower memory

HEADERS = {
    "User-Agent": "SentimentAnalysisPrototype/1.0 (Team1 Capstone Project)"
}

# ─────────────────────────────────────────────
#  STEP 1 — SCRAPE REDDIT VIA PUBLIC JSON
# ─────────────────────────────────────────────

def scrape_subreddit(subreddit: str, keyword: str, limit: int = 100) -> list:
    """
    Uses Reddit's /search.json endpoint scoped to a single subreddit.
    This searches directly for posts matching the keyword, rather than
    fetching all hot posts and filtering — giving far more keyword matches
    per request and allowing us to reliably hit the target limit.

    URL pattern:
      /r/{subreddit}/search.json?q={keyword}&restrict_sr=on&sort=relevance&limit=100
    """
    all_posts = []
    after     = None
    remaining = limit

    print(f"\n[SCRAPING] r/{subreddit} — searching '{keyword}', up to {limit} posts")

    while remaining > 0:
        batch = min(remaining, 100)
        url = (
            f"https://www.reddit.com/r/{subreddit}/search.json"
            f"?q={requests.utils.quote(keyword)}"
            f"&restrict_sr=on"
            f"&sort=relevance"
            f"&limit={batch}"
        )
        if after:
            url += f"&after={after}"

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"  [ERROR] {e}")
            break

        data = r.json()
        page = data.get("data", {}).get("children", [])
        if not page:
            break

        all_posts.extend(page)
        remaining -= len(page)
        after = data.get("data", {}).get("after")
        if not after:
            break

        print(f"  [PAGE]  {len(all_posts)} posts fetched so far…")
        time.sleep(2)

    print(f"  [OK]    {len(all_posts)} posts from r/{subreddit}")
    time.sleep(2)
    return all_posts


def parse_posts(raw: list, subreddit: str) -> list:
    """
    Parses raw Reddit post data into our standard schema.
    No keyword filter needed here — the search endpoint already
    returned only relevant posts.
    """
    parsed = []

    for item in raw:
        p     = item.get("data", {})
        title = p.get("title", "")
        body  = p.get("selftext", "")

        # Skip deleted / empty posts
        if not title and not body:
            continue

        ts = datetime.datetime.fromtimestamp(
            p.get("created_utc", 0),
            tz=datetime.timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S")

        parsed.append({
            "platform":     "Reddit",
            "subreddit":    subreddit,
            "post_id":      p.get("id", ""),
            "title":        title,
            "body":         body[:1000],
            "upvotes":      p.get("score", 0),
            "upvote_ratio": p.get("upvote_ratio", 0),
            "num_comments": p.get("num_comments", 0),
            "timestamp":    ts,
            "url":          "https://reddit.com" + p.get("permalink", ""),
            "sentiment":    None,
            "confidence":   None,
        })

    return parsed


# ─────────────────────────────────────────────
#  STEP 2 — SENTIMENT VIA OLLAMA
# ─────────────────────────────────────────────

def classify_sentiment(text: str) -> dict:
    if not text.strip():
        return {"label": "neutral", "confidence": "low"}

    clean = text.strip().replace("\n", " ")[:500]
    prompt = (
        "Classify the sentiment of the following Reddit post about a brand.\n"
        "Reply with ONLY a JSON object, no explanation:\n"
        '{"sentiment": "positive", "confidence": "high"}\n\n'
        "sentiment: positive | neutral | negative\n"
        "confidence: high | medium | low\n\n"
        f"Post: {clean}"
    )

    # FIX: 3-attempt retry with escalating timeouts.
    # Gemma cold-starts on the first 1-2 posts and can exceed 60s.
    # 120s → 150s → 180s covers model warm-up without hanging indefinitely.
    timeouts = [120, 150, 180]
    for attempt, timeout in enumerate(timeouts, start=1):
        try:
            r = requests.post(
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=timeout,
            )
            r.raise_for_status()
            raw = r.json().get("response", "").strip()
            s, e = raw.find("{"), raw.rfind("}") + 1
            if s != -1 and e > s:
                res = json.loads(raw[s:e])
                return {
                    "label":      res.get("sentiment", "neutral"),
                    "confidence": res.get("confidence", "medium"),
                }
            # Response came back but JSON wasn't parseable — no point retrying
            break
        except requests.exceptions.Timeout:
            if attempt < len(timeouts):
                next_t = timeouts[attempt]
                print(f"    [WARN] Timeout on attempt {attempt} "
                      f"— retrying with {next_t}s limit…")
            else:
                print(f"    [WARN] Timed out after {len(timeouts)} attempts — skipping.")
        except Exception as ex:
            print(f"    [WARN] {ex}")
            break

    return {"label": "neutral", "confidence": "low"}


def run_sentiment(posts: list) -> list:
    total = len(posts)
    print(f"\n[SENTIMENT] Classifying {total} posts with {OLLAMA_MODEL}…\n")

    for i, post in enumerate(posts):
        res = classify_sentiment(f"{post['title']} {post['body']}")
        post["sentiment"]  = res["label"]
        post["confidence"] = res["confidence"]
        print(f"  [{i+1:>3}/{total}] {res['label'].upper():8} "
              f"({res['confidence']:6}) | {post['title'][:55]}")
        time.sleep(0.3)

    return posts


# ─────────────────────────────────────────────
#  STEP 3 — SAVE & SUMMARISE
# ─────────────────────────────────────────────

def save(posts, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
    print(f"\n[SAVED] {len(posts)} posts → '{filename}'")


def summarise(posts):
    if not posts:
        return
    c  = {"positive": 0, "neutral": 0, "negative": 0}
    hi = 0
    for p in posts:
        label = p.get("sentiment", "neutral")
        c[label] = c.get(label, 0) + 1
        if p.get("confidence") == "high":
            hi += 1
    t = len(posts)
    print("\n" + "=" * 56)
    print(f"  SENTIMENT SUMMARY — '{KEYWORD}'")
    print("=" * 56)
    print(f"  Total posts          : {t}")
    print(f"  Positive             : {c['positive']:>4}  ({c['positive']/t*100:5.1f}%)")
    print(f"  Neutral              : {c['neutral']:>4}  ({c['neutral']/t*100:5.1f}%)")
    print(f"  Negative             : {c['negative']:>4}  ({c['negative']/t*100:5.1f}%)")
    print(f"  High-confidence      : {hi:>4}  ({hi/t*100:5.1f}%)")
    print(f"  Model                : {OLLAMA_MODEL}")
    print(f"  Output               : {OUTPUT_FILE}")
    print("=" * 56 + "\n")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    print("\n" + "=" * 56)
    print("  Reddit Scraper v4 — Team 1")
    print("=" * 56)
    print(f"  Subreddits : {', '.join(SUBREDDITS)}")
    print(f"  Keyword    : {KEYWORD}  |  Posts/sub: {POST_LIMIT}  |  Total cap: {TOTAL_LIMIT}")
    print(f"  Model      : {OLLAMA_MODEL}")
    print("=" * 56)

    all_posts = []
    for sub in SUBREDDITS:
        if len(all_posts) >= TOTAL_LIMIT:
            print(f"[SKIP]  Total cap ({TOTAL_LIMIT}) reached — skipping r/{sub}")
            break
        budget = min(POST_LIMIT, TOTAL_LIMIT - len(all_posts))
        raw    = scrape_subreddit(sub, KEYWORD, budget)
        parsed = parse_posts(raw, sub)
        all_posts.extend(parsed)

    if not all_posts:
        print("\n[DONE] No posts matched. Try broader keyword or different subreddits.")
        return

    print(f"\n[COLLECTED] {len(all_posts)} total matching posts")

    seen, deduped = set(), []
    for p in all_posts:
        if p["post_id"] not in seen:
            seen.add(p["post_id"])
            deduped.append(p)
    print(f"[DEDUPED]   {len(deduped)} after removing {len(all_posts)-len(deduped)} duplicate(s)")

    if len(deduped) > TOTAL_LIMIT:
        print(f"[TRIM]    {len(deduped)} → {TOTAL_LIMIT} posts (hard cap)")
        deduped = deduped[:TOTAL_LIMIT]

    final = run_sentiment(deduped)
    save(final, OUTPUT_FILE)
    summarise(final)


if __name__ == "__main__":
    main()
