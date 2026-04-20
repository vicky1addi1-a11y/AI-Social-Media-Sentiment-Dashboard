"""
X (Twitter) Sentiment Scraper — Team 1 Prototype (v8)
Fixes blank likes/retweets/replies/username by inspecting actual
Scweet field names from the first result and mapping them dynamically.

SETUP:
  1. pip3 install -U Scweet requests
  2. Log into x.com → DevTools (Cmd+Option+I) → Application tab
     → Cookies → https://x.com → copy the value of "auth_token"
  3. Paste it into AUTH_TOKEN below.
  4. python3 x_scraper.py

Requirements:
    pip3 install -U Scweet requests
"""

import json
import time
import os
import datetime
import requests

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

AUTH_TOKEN = ""

SEARCH_QUERIES = [
    "Nike shoes",
    "Nike running",
    "#Nike",
    "Nike brand",
]

PER_QUERY_LIMIT = 15
TOTAL_LIMIT     = 60
OUTPUT_FILE     = "x_data.json"
DB_FILE         = "scweet_state.db"

SINCE_DATE = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
UNTIL_DATE = datetime.date.today().strftime("%Y-%m-%d")

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma4:e4b-it-q4_K_M"   # Change to gemma4:e4b-it-q4_K_M for 4-bit

# ─────────────────────────────────────────────
#  FIELD MAP — populated automatically on first result
# ─────────────────────────────────────────────

# This dict is filled by inspect_fields() and used by parse_row().
# It maps our standard names to whatever Scweet actually returns.
FIELD_MAP: dict[str, str] = {}

def inspect_fields(row: dict):
    """
    Called once on the first result row.
    Prints every field Scweet returned and builds FIELD_MAP
    so engagement metrics are read from the correct keys.
    """
    global FIELD_MAP
    if FIELD_MAP:
        return  # Already done

    print("\n[FIELDS] Inspecting actual Scweet field names from first tweet:")
    for k, v in row.items():
        print(f"  {k!r:40} = {str(v)[:60]}")
    print()

    # ── Text ────────────────────────────────────────────────────────
    FIELD_MAP["text"] = _find_key(row, [
        "tweet_text", "Embedded_text", "full_text", "text", "content",
    ])

    # ── ID ──────────────────────────────────────────────────────────
    FIELD_MAP["id"] = _find_key(row, [
        "id", "tweet_id", "TweetID", "Tweet_id", "Status_id",
    ])

    # ── Username ────────────────────────────────────────────────────
    FIELD_MAP["username"] = _find_key(row, [
        "user_handle",       # Scweet v4 GraphQL
        "Username",          # Scweet v3
        "UserScreenName",    # Scweet v3 alt
        "username",
        "user",
        "screen_name",
        "author",
        "author_handle",
        "name",
    ])

    # ── Likes ────────────────────────────────────────────────────────
    FIELD_MAP["likes"] = _find_key(row, [
        "tweet_favorite_count",  # v4
        "Likes",                 # v3
        "favorite_count",
        "favorites",
        "likes",
        "like_count",
        "heart_count",
    ])

    # ── Retweets ─────────────────────────────────────────────────────
    FIELD_MAP["retweets"] = _find_key(row, [
        "tweet_retweet_count",   # v4
        "Retweets",              # v3
        "retweet_count",
        "retweets",
        "rt_count",
        "reshare_count",
    ])

    # ── Replies ──────────────────────────────────────────────────────
    FIELD_MAP["replies"] = _find_key(row, [
        "tweet_reply_count",     # v4
        "Comments",              # v3
        "reply_count",
        "replies",
        "comment_count",
        "response_count",
    ])

    # ── Timestamp ────────────────────────────────────────────────────
    FIELD_MAP["timestamp"] = _find_key(row, [
        "tweet_created_at",  # v4
        "Timestamp",         # v3
        "created_at",
        "timestamp",
        "date",
        "posted_at",
    ])

    # ── URL ──────────────────────────────────────────────────────────
    FIELD_MAP["url"] = _find_key(row, [
        "tweet_url",    # v4
        "Tweet_URL",    # v3
        "url",
        "link",
        "permalink",
    ])

    print("[FIELDS] Resolved field map:")
    for std, actual in FIELD_MAP.items():
        print(f"  {std:12} → '{actual}'" if actual else f"  {std:12} → NOT FOUND")
    print()


def _find_key(row: dict, candidates: list[str]) -> str:
    """Return the first candidate key that exists in row, or ''."""
    for k in candidates:
        if k in row:
            return k
    return ""


def get_mapped(row: dict, field: str, default=""):
    """Read a value using the resolved FIELD_MAP."""
    key = FIELD_MAP.get(field, "")
    if not key:
        return default
    val = row.get(key)
    return default if val in (None, "", "nan", "None") else val


# ─────────────────────────────────────────────
#  RESET STATE
# ─────────────────────────────────────────────

def reset_scweet_state():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"[RESET]  Deleted '{DB_FILE}' — account limits cleared.")
    else:
        print(f"[RESET]  No existing '{DB_FILE}' — starting fresh.")


# ─────────────────────────────────────────────
#  ROW PARSER
# ─────────────────────────────────────────────

def parse_row(row, query: str) -> dict | None:
    if hasattr(row, "to_dict"):
        row = row.to_dict()

    # Inspect fields on the very first row we process
    inspect_fields(row)

    text = str(get_mapped(row, "text", "")).strip()
    if not text or text.lower() in ("nan", "none", ""):
        return None

    return {
        "platform":   "X",
        "query":      query,
        "tweet_id":   str(get_mapped(row, "id", "")).replace("tweet-", ""),
        "text":       text,
        "username":   str(get_mapped(row, "username", "")),
        "likes":      _to_int(get_mapped(row, "likes",    0)),
        "retweets":   _to_int(get_mapped(row, "retweets", 0)),
        "replies":    _to_int(get_mapped(row, "replies",  0)),
        "timestamp":  str(get_mapped(row, "timestamp", "")),
        "url":        str(get_mapped(row, "url", "")),
        "sentiment":  None,
        "confidence": None,
    }


def _to_int(val) -> int:
    try:
        return int(float(str(val))) if val not in (None, "", "nan") else 0
    except (ValueError, TypeError):
        return 0


# ─────────────────────────────────────────────
#  STEP 1 — COLLECT TWEETS
# ─────────────────────────────────────────────

def search_with_retry(s, query: str, limit: int, max_retries: int = 3) -> list:
    try:
        from Scweet.exceptions import AccountPoolExhausted
    except ImportError:
        AccountPoolExhausted = Exception

    for attempt in range(1, max_retries + 1):
        try:
            results = s.search(
                query,
                since=SINCE_DATE,
                until=UNTIL_DATE,
                limit=limit,
                lang="en",
                save=False,
            )
            return results if results is not None else []

        except AccountPoolExhausted:
            if attempt < max_retries:
                print(f"  [WAIT]  Account pool exhausted — waiting 60s "
                      f"(retry {attempt}/{max_retries})…")
                time.sleep(60)
            else:
                print(f"  [SKIP]  Still exhausted after {max_retries} retries — "
                      f"skipping '{query}'.")
                return []
        except Exception as e:
            print(f"  [ERROR] {type(e).__name__}: {e}")
            return []

    return []


def collect_tweets() -> list:
    if AUTH_TOKEN == "paste_your_auth_token_here":
        print("[ERROR] Paste your auth_token from browser DevTools first.")
        raise SystemExit(1)

    reset_scweet_state()

    print("[AUTH]  Initialising Scweet…")
    try:
        from Scweet import Scweet
        s = Scweet(auth_token=AUTH_TOKEN)
    except Exception as e:
        print(f"[ERROR] {e}")
        raise SystemExit(1)

    print(f"[PLAN]  {len(SEARCH_QUERIES)} queries × {PER_QUERY_LIMIT} "
          f"= {len(SEARCH_QUERIES)*PER_QUERY_LIMIT} target  |  cap: {TOTAL_LIMIT}\n")

    all_tweets = []

    for query in SEARCH_QUERIES:
        if len(all_tweets) >= TOTAL_LIMIT:
            print(f"[SKIP]  Total cap reached.")
            break

        budget = min(PER_QUERY_LIMIT, TOTAL_LIMIT - len(all_tweets))
        print(f"[SEARCHING] '{query}' — limit {budget}")

        results = search_with_retry(s, query, budget)

        if hasattr(results, "to_dict"):
            rows = results.to_dict(orient="records")
        elif hasattr(results, "iterrows"):
            rows = [r.to_dict() for _, r in results.iterrows()]
        else:
            rows = list(results)

        existing_ids  = {t["tweet_id"] for t in all_tweets if t["tweet_id"]}
        existing_text = {t["text"][:80] for t in all_tweets}

        added = 0
        for row in rows:
            if added >= budget:
                break
            tweet = parse_row(row, query)
            if not tweet:
                continue
            if tweet["tweet_id"] in existing_ids or tweet["text"][:80] in existing_text:
                continue
            all_tweets.append(tweet)
            existing_ids.add(tweet["tweet_id"])
            existing_text.add(tweet["text"][:80])
            added += 1

        print(f"  [OK]    {added} tweets added (total: {len(all_tweets)})")
        time.sleep(3)

    if len(all_tweets) > TOTAL_LIMIT:
        all_tweets = all_tweets[:TOTAL_LIMIT]

    print(f"\n[COLLECTED] {len(all_tweets)} tweets ready for sentiment analysis")
    return all_tweets


# ─────────────────────────────────────────────
#  STEP 2 — SENTIMENT VIA OLLAMA
# ─────────────────────────────────────────────

def classify_sentiment(text: str) -> dict:
    clean = text.strip().replace("\n", " ")[:300]
    prompt = (
        'Classify this tweet about a brand.\n'
        'Reply ONLY with JSON: {"sentiment":"positive","confidence":"high"}\n'
        'sentiment: positive|neutral|negative  confidence: high|medium|low\n\n'
        f'Tweet: {clean}'
    )
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        r.raise_for_status()
        raw = r.json().get("response", "")
        s, e = raw.find("{"), raw.rfind("}") + 1
        if s != -1 and e > s:
            res = json.loads(raw[s:e])
            return {"label": res.get("sentiment", "neutral"),
                    "confidence": res.get("confidence", "medium")}
    except Exception:
        pass
    return {"label": "neutral", "confidence": "low"}


def run_sentiment(tweets: list) -> list:
    total = len(tweets)
    print(f"\n[SENTIMENT] Classifying {total} tweets with {OLLAMA_MODEL}…\n")
    for i, tweet in enumerate(tweets):
        res = classify_sentiment(tweet["text"])
        tweet["sentiment"]  = res["label"]
        tweet["confidence"] = res["confidence"]
        print(f"  [{i+1:>3}/{total}] {res['label'].upper():8} "
              f"({res['confidence']:6}) | {tweet['text'][:55]}")
        time.sleep(0.2)
    return tweets


# ─────────────────────────────────────────────
#  STEP 3 — SAVE & SUMMARISE
# ─────────────────────────────────────────────

def save(tweets, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(tweets, f, indent=2, ensure_ascii=False)
    print(f"\n[SAVED] {len(tweets)} tweets → '{filename}'")


def summarise(tweets):
    if not tweets:
        return
    c  = {"positive": 0, "neutral": 0, "negative": 0}
    hi = 0
    per_query: dict = {}
    for t in tweets:
        label = t.get("sentiment", "neutral")
        c[label] = c.get(label, 0) + 1
        if t.get("confidence") == "high":
            hi += 1
        q = t.get("query", "?")
        per_query[q] = per_query.get(q, 0) + 1

    # Sample engagement stats
    likes_total    = sum(t.get("likes", 0) for t in tweets)
    retweet_total  = sum(t.get("retweets", 0) for t in tweets)
    username_found = sum(1 for t in tweets if t.get("username"))

    n = len(tweets)
    print("\n" + "=" * 56)
    print("  X SENTIMENT SUMMARY")
    print("=" * 56)
    print(f"  Date range      : {SINCE_DATE} → {UNTIL_DATE}")
    print(f"  Total tweets    : {n}")
    print(f"  Positive        : {c['positive']:>4}  ({c['positive']/n*100:5.1f}%)")
    print(f"  Neutral         : {c['neutral']:>4}  ({c['neutral']/n*100:5.1f}%)")
    print(f"  Negative        : {c['negative']:>4}  ({c['negative']/n*100:5.1f}%)")
    print(f"  High-confidence : {hi:>4}  ({hi/n*100:5.1f}%)")
    print(f"  Total likes     : {likes_total}")
    print(f"  Total retweets  : {retweet_total}")
    print(f"  Usernames found : {username_found}/{n}")
    print(f"  Per query:")
    for q, count in per_query.items():
        print(f"    '{q}': {count}")
    print(f"  Model           : {OLLAMA_MODEL}")
    print(f"  Output          : {OUTPUT_FILE}")
    print("=" * 56 + "\n")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    print("\n" + "=" * 56)
    print("  X Scraper v8 — Team 1")
    print("=" * 56)
    print(f"  Queries    : {', '.join(SEARCH_QUERIES)}")
    print(f"  Per-query  : {PER_QUERY_LIMIT}  |  Total cap: {TOTAL_LIMIT}")
    print(f"  Model      : {OLLAMA_MODEL}")
    print(f"  Date range : {SINCE_DATE} → {UNTIL_DATE}")
    print("=" * 56)

    tweets = collect_tweets()
    if not tweets:
        print("\n[DONE] No tweets collected. Check auth_token and try again.")
        return

    final = run_sentiment(tweets)
    save(final, OUTPUT_FILE)
    summarise(final)


if __name__ == "__main__":
    main()
