"""
X (Twitter) Sentiment Scraper — Team 1 Prototype (v9)

CHANGES FROM v8:
  - Reply count: added NbReplies, replyCount, replies_count as field
    candidates so the count no longer shows 0 in the output.
  - Top-5 replies: after collecting all tweets, fetches up to 5 replies
    for the top 3 most-engaged tweets (by likes + retweets). Replies are
    stored in a "top_replies" list inside the parent tweet's JSON record,
    each reply also classified for sentiment by Gemma.
  - Reply totals now counted and printed in the summary.
  - Reply fetching is limited to 3 tweets to avoid exhausting the single
    account's daily Scweet lease limit.

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

PER_QUERY_LIMIT  = 15
TOTAL_LIMIT      = 60
REPLIES_PER_TWEET = 5    # Max replies fetched per parent tweet
REPLY_FETCH_TOP_N = 3    # Only fetch replies for the N most-engaged tweets

OUTPUT_FILE = "x_data.json"
DB_FILE     = "scweet_state.db"

SINCE_DATE = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
UNTIL_DATE = datetime.date.today().strftime("%Y-%m-%d")

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma4:e4b-it-q8_0"   # Change to gemma4:e4b-it-q4_K_M for 4-bit

# ─────────────────────────────────────────────
#  FIELD MAP
# ─────────────────────────────────────────────

FIELD_MAP: dict[str, str] = {}


def inspect_fields(row: dict):
    global FIELD_MAP
    if FIELD_MAP:
        return

    print("\n[FIELDS] Actual Scweet field names from first tweet:")
    for k, v in row.items():
        print(f"  {k!r:40} = {str(v)[:60]}")
    print()

    FIELD_MAP["text"]      = _find_key(row, ["tweet_text", "Embedded_text", "full_text", "text", "content"])
    FIELD_MAP["id"]        = _find_key(row, ["id", "tweet_id", "TweetID", "Tweet_id", "Status_id"])
    FIELD_MAP["username"]  = _find_key(row, ["user_handle", "Username", "UserScreenName", "username",
                                              "user", "screen_name", "author", "author_handle", "name"])
    FIELD_MAP["likes"]     = _find_key(row, ["tweet_favorite_count", "Likes", "favorite_count",
                                              "favorites", "likes", "like_count", "NbLikes"])
    FIELD_MAP["retweets"]  = _find_key(row, ["tweet_retweet_count", "Retweets", "retweet_count",
                                              "retweets", "rt_count", "NbRetweets"])
    # FIX: added NbReplies, replyCount, replies_count — common Scweet field names for replies
    FIELD_MAP["replies"]   = _find_key(row, ["tweet_reply_count", "NbReplies", "replyCount",
                                              "replies_count", "Comments", "reply_count",
                                              "replies", "comment_count", "response_count"])
    FIELD_MAP["timestamp"] = _find_key(row, ["tweet_created_at", "Timestamp", "created_at",
                                              "timestamp", "date", "posted_at"])
    FIELD_MAP["url"]       = _find_key(row, ["tweet_url", "Tweet_URL", "url", "link", "permalink"])

    print("[FIELDS] Resolved map:")
    for std, actual in FIELD_MAP.items():
        status = f"→ '{actual}'" if actual else "→ NOT FOUND (will default to 0/empty)"
        print(f"  {std:12} {status}")
    print()


def _find_key(row: dict, candidates: list) -> str:
    for k in candidates:
        if k in row:
            return k
    return ""


def extract_username(raw_val) -> str:
    """
    Scweet sometimes returns the user field as a dict like
    {'screen_name': 'Nike', 'name': 'Nike'}  instead of a plain string.
    This helper always returns a clean screen_name string.
    """
    if isinstance(raw_val, dict):
        return str(raw_val.get("screen_name") or raw_val.get("name") or "").strip()
    val = str(raw_val or "").strip()
    return "" if val.lower() in ("nan", "none", "") else val


def get_mapped(row: dict, field: str, default=""):
    key = FIELD_MAP.get(field, "")
    if not key:
        return default
    val = row.get(key)
    return default if val in (None, "", "nan", "None") else val


def _to_int(val) -> int:
    try:
        return int(float(str(val))) if val not in (None, "", "nan") else 0
    except (ValueError, TypeError):
        return 0


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

    inspect_fields(row)

    text = str(get_mapped(row, "text", "")).strip()
    if not text or text.lower() in ("nan", "none", ""):
        return None

    return {
        "platform":    "X",
        "query":       query,
        "tweet_id":    str(get_mapped(row, "id", "")).replace("tweet-", ""),
        "text":        text,
        "username":    extract_username(get_mapped(row, "username", "")),
        "likes":       _to_int(get_mapped(row, "likes",    0)),
        "retweets":    _to_int(get_mapped(row, "retweets", 0)),
        "reply_count": _to_int(get_mapped(row, "replies",  0)),
        "timestamp":   str(get_mapped(row, "timestamp", "")),
        "url":         str(get_mapped(row, "url", "")),
        "sentiment":   None,
        "confidence":  None,
        "top_replies": [],   # Filled later by fetch_replies()
    }


# ─────────────────────────────────────────────
#  STEP 1a — COLLECT MAIN TWEETS
# ─────────────────────────────────────────────

def search_with_retry(s, query: str, limit: int,
                      to_account: str = "", max_retries: int = 3) -> list:
    try:
        from Scweet.exceptions import AccountPoolExhausted
    except ImportError:
        AccountPoolExhausted = Exception

    kwargs = dict(
        since=SINCE_DATE,
        until=UNTIL_DATE,
        limit=limit,
        lang="en",
        save=False,
    )
    if to_account:
        kwargs["to_account"] = to_account

    for attempt in range(1, max_retries + 1):
        try:
            results = s.search(query, **kwargs)
            return results if results is not None else []
        except AccountPoolExhausted:
            if attempt < max_retries:
                print(f"  [WAIT]  Account pool exhausted — waiting 60s "
                      f"(retry {attempt}/{max_retries})…")
                time.sleep(60)
            else:
                print(f"  [SKIP]  Still exhausted after {max_retries} retries.")
                return []
        except Exception as e:
            print(f"  [ERROR] {type(e).__name__}: {e}")
            return []
    return []


def normalise_rows(results) -> list:
    if results is None:
        return []
    if hasattr(results, "to_dict"):
        return results.to_dict(orient="records")
    if hasattr(results, "iterrows"):
        return [r.to_dict() for _, r in results.iterrows()]
    return list(results)


def collect_tweets(s) -> list:
    print(f"[PLAN]  {len(SEARCH_QUERIES)} queries × {PER_QUERY_LIMIT} "
          f"= {len(SEARCH_QUERIES)*PER_QUERY_LIMIT} target  |  cap: {TOTAL_LIMIT}\n")

    all_tweets = []

    for query in SEARCH_QUERIES:
        if len(all_tweets) >= TOTAL_LIMIT:
            print(f"[SKIP]  Total cap reached.")
            break

        budget = min(PER_QUERY_LIMIT, TOTAL_LIMIT - len(all_tweets))
        print(f"[SEARCHING] '{query}' — limit {budget}")

        rows = normalise_rows(search_with_retry(s, query, budget))

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

        if added == 0 and rows:
            first = rows[0] if isinstance(rows[0], dict) else rows[0].to_dict()
            print(f"  [DEBUG] Raw keys: {list(first.keys())[:12]}")

        print(f"  [OK]    {added} tweets added (total: {len(all_tweets)})")
        time.sleep(3)

    if len(all_tweets) > TOTAL_LIMIT:
        all_tweets = all_tweets[:TOTAL_LIMIT]

    return all_tweets


# ─────────────────────────────────────────────
#  STEP 1b — FETCH TOP 5 REPLIES FOR TOP TWEETS
# ─────────────────────────────────────────────

def fetch_replies(s, tweets: list) -> list:
    """
    For the REPLY_FETCH_TOP_N most-engaged tweets that have a username,
    searches for up to REPLIES_PER_TWEET replies using Scweet's to_account
    parameter scoped to a ±1 day window around the tweet timestamp.
    Stores results in tweet["top_replies"] as a list of dicts.
    """
    # Sort by total engagement to pick the most interesting tweets
    eligible = [
        t for t in tweets
        if t.get("username") and t["username"] not in ("", "nan", "None")
    ]
    eligible.sort(key=lambda t: t.get("likes", 0) + t.get("retweets", 0), reverse=True)
    targets = eligible[:REPLY_FETCH_TOP_N]

    if not targets:
        print("\n[REPLIES] No tweets with usernames found — skipping reply fetch.")
        return tweets

    print(f"\n[REPLIES] Fetching up to {REPLIES_PER_TWEET} replies for "
          f"{len(targets)} most-engaged tweets…")

    for tweet in targets:
        username  = tweet["username"].lstrip("@")
        ts_str    = tweet.get("timestamp", "")

        # Build a ±1 day window around the tweet timestamp
        try:
            base   = datetime.datetime.strptime(ts_str[:10], "%Y-%m-%d").date()
            r_since = (base - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            r_until = (base + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            r_since, r_until = SINCE_DATE, UNTIL_DATE

        # Use X's native '@username' search syntax — 'to_account' is not a valid Scweet param
        reply_query = f"@{username}"
        print(f"  [→ @{username}]  query='{reply_query}'  window {r_since} → {r_until}")

        try:
            results = s.search(
                reply_query,
                since=r_since,
                until=r_until,
                limit=REPLIES_PER_TWEET,
                lang="en",
                save=False,
            )

            rows = normalise_rows(results)
            replies = []
            for row in rows[:REPLIES_PER_TWEET]:
                if hasattr(row, "to_dict"):
                    row = row.to_dict()
                text = str(get_mapped(row, "text", "")).strip()
                if text and text.lower() not in ("nan", "none", ""):
                    replies.append({
                        "reply_id":   str(get_mapped(row, "id", "")).replace("tweet-", ""),
                        "text":       text,
                        "username":   extract_username(get_mapped(row, "username", "")),
                        "likes":      _to_int(get_mapped(row, "likes",    0)),
                        "retweets":   _to_int(get_mapped(row, "retweets", 0)),
                        "timestamp":  str(get_mapped(row, "timestamp", "")),
                        "sentiment":  None,
                        "confidence": None,
                    })

            tweet["top_replies"] = replies
            print(f"     {len(replies)} replies fetched")

        except Exception as e:
            print(f"  [WARN]  Could not fetch replies for @{username}: {e}")
            tweet["top_replies"] = []

        time.sleep(3)

    return tweets


# ─────────────────────────────────────────────
#  STEP 2 — SENTIMENT VIA OLLAMA
# ─────────────────────────────────────────────

def classify_sentiment(text: str) -> dict:
    clean = text.strip().replace("\n", " ")[:300]
    prompt = (
        "Classify this tweet about a brand.\n"
        'Reply ONLY with JSON: {"sentiment":"positive","confidence":"high"}\n'
        "sentiment: positive|neutral|negative  confidence: high|medium|low\n\n"
        f"Tweet: {clean}"
    )
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
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
    # Count how many items need classifying (tweets + all replies)
    reply_count = sum(len(t.get("top_replies", [])) for t in tweets)
    total = len(tweets) + reply_count
    done  = 0

    print(f"\n[SENTIMENT] Classifying {len(tweets)} tweets "
          f"+ {reply_count} replies = {total} total with {OLLAMA_MODEL}…\n")

    for tweet in tweets:
        done += 1
        res = classify_sentiment(tweet["text"])
        tweet["sentiment"]  = res["label"]
        tweet["confidence"] = res["confidence"]
        print(f"  [{done:>3}/{total}] {res['label'].upper():8} "
              f"({res['confidence']:6}) | {tweet['text'][:50]}")
        time.sleep(0.2)

        # Classify each reply too
        for reply in tweet.get("top_replies", []):
            done += 1
            res = classify_sentiment(reply["text"])
            reply["sentiment"]  = res["label"]
            reply["confidence"] = res["confidence"]
            print(f"  [{done:>3}/{total}]   REPLY {res['label'].upper():8} "
                  f"| {reply['text'][:46]}")
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
    total_reply_count = 0   # Sum of reply_count fields (X's reported number)
    total_replies_fetched = 0

    for t in tweets:
        label = t.get("sentiment", "neutral")
        c[label] = c.get(label, 0) + 1
        if t.get("confidence") == "high":
            hi += 1
        q = t.get("query", "?")
        per_query[q] = per_query.get(q, 0) + 1
        total_reply_count    += t.get("reply_count", 0)
        total_replies_fetched += len(t.get("top_replies", []))

    likes_total   = sum(t.get("likes", 0) for t in tweets)
    retweet_total = sum(t.get("retweets", 0) for t in tweets)
    usernames     = sum(1 for t in tweets if t.get("username"))

    n = len(tweets)
    print("\n" + "=" * 56)
    print("  X SENTIMENT SUMMARY")
    print("=" * 56)
    print(f"  Date range           : {SINCE_DATE} → {UNTIL_DATE}")
    print(f"  Total tweets         : {n}")
    print(f"  Positive             : {c['positive']:>4}  ({c['positive']/n*100:5.1f}%)")
    print(f"  Neutral              : {c['neutral']:>4}  ({c['neutral']/n*100:5.1f}%)")
    print(f"  Negative             : {c['negative']:>4}  ({c['negative']/n*100:5.1f}%)")
    print(f"  High-confidence      : {hi:>4}  ({hi/n*100:5.1f}%)")
    print(f"  Total likes          : {likes_total}")
    print(f"  Total retweets       : {retweet_total}")
    print(f"  Total replies (X #)  : {total_reply_count}")
    print(f"  Replies fetched/analyzed : {total_replies_fetched}")
    print(f"  Usernames found      : {usernames}/{n}")
    print(f"  Per query:")
    for q, count in per_query.items():
        print(f"    '{q}': {count}")
    print(f"  Model                : {OLLAMA_MODEL}")
    print(f"  Output               : {OUTPUT_FILE}")
    print("=" * 56 + "\n")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    print("\n" + "=" * 56)
    print("  X Scraper v9 — Team 1")
    print("=" * 56)
    print(f"  Queries    : {', '.join(SEARCH_QUERIES)}")
    print(f"  Per-query  : {PER_QUERY_LIMIT}  |  Total cap: {TOTAL_LIMIT}")
    print(f"  Replies    : top {REPLIES_PER_TWEET} for {REPLY_FETCH_TOP_N} most-engaged tweets")
    print(f"  Model      : {OLLAMA_MODEL}")
    print(f"  Date range : {SINCE_DATE} → {UNTIL_DATE}")
    print("=" * 56)

    if AUTH_TOKEN == "paste_your_auth_token_here":
        print("[ERROR] Paste your auth_token from browser DevTools first.")
        return

    reset_scweet_state()

    print("[AUTH]  Initialising Scweet…")
    try:
        from Scweet import Scweet
        s = Scweet(auth_token=AUTH_TOKEN)
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    tweets = collect_tweets(s)
    if not tweets:
        print("\n[DONE] No tweets collected. Check auth_token and try again.")
        return

    print(f"\n[COLLECTED] {len(tweets)} tweets ready")

    tweets = fetch_replies(s, tweets)

    final = run_sentiment(tweets)
    save(final, OUTPUT_FILE)
    summarise(final)


if __name__ == "__main__":
    main()
