import os
import requests
import json
import time
import re

# --- 設定値 ---
X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

LAST_ID_FILE = "last_id.txt"
# 動作実績のある安定モデルを優先
MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
MAX_NOTIFY_COUNT = 20  # 1通にまとめる最大件数

PROMPT_TEMPLATE = """
以下のSNSの投稿本文を読み、投稿者が「品川近視クリニックの紹介・割引クーポン・紹介コードを求めている（探している・使いたい）」かどうかを判定してください。

【判定基準】
- 投稿者がクーポンや紹介を求めている、探している、欲しいと言っている場合は「YES」
- 既に受けた感想、自分が紹介を配っている側、クリニックの宣伝、無関係な話題の場合は「NO」

回答は必ず以下のJSON形式のみで出力してください（マークダウンの```は不要です）：
{{"is_target": true, "reason": "判定理由を日本語で簡潔に"}}
または
{{"is_target": false, "reason": "判定理由を日本語で簡潔に"}}

【投稿本文】
{text}
"""

def get_last_id():
    """しおり（前回の最新投稿ID）を読み込む"""
    if os.path.exists(LAST_ID_FILE):
        with open(LAST_ID_FILE, "r", encoding="utf-8") as f:
            val = f.read().strip()
            if val:
                return val
    return None

def save_last_id(tweet_id):
    """しおりをファイルに保存する"""
    with open(LAST_ID_FILE, "w", encoding="utf-8") as f:
        f.write(str(tweet_id))

def search_tweets(since_id=None):
    """Xから検索する"""
    url = "https://api.twitter.com/2/tweets/search/recent"
    query = "品川近視 -is:retweet lang:ja"
    params = {
        "query": query,
        "max_results": 100,
        "tweet.fields": "created_at,text,author_id"
    }
    if since_id:
        params["since_id"] = since_id

    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        data = res.json()
        return data.get("data", [])
    else:
        print(f"❌ X APIエラー ({res.status_code}): {res.text}")
        return []

def judge_with_ai(post_text):
    """Geminiで判定する"""
    prompt = PROMPT_TEMPLATE.format(text=post_text)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for model_id in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
        for retry in range(2):
            try:
                res = requests.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    params={"key": GEMINI_API_KEY},
                    json=payload,
                    timeout=15
                )
                if res.status_code == 200:
                    text_resp = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    # JSON部分を安全に抽出
                    match = re.search(r'\{.*\}', text_resp, re.DOTALL)
                    if match:
                        parsed = json.loads(match.group(0))
                        return parsed.get("is_target", False), parsed.get("reason", "")
                    else:
                        print(f"⚠️ JSON抽出失敗: {text_resp}")
                elif res.status_code == 503:
                    print(f"⚠️ {model_id} 混雑中(503)。リトライします...")
                    time.sleep(2)
                else:
                    print(f"⚠️ Geminiエラー ({model_id}, ステータス {res.status_code}): {res.text}")
                    break
            except Exception as e:
                print(f"⚠️ 通信例外 ({model_id}): {e}")
                time.sleep(1)

    return False, "AI判定に失敗しました"

def send_combined_line(targets):
    """複数件を1通にまとめてLINE通知する"""
    if not targets:
        return

    count = len(targets)
    msg_lines = [f"🎯【品川近視 クーポン希望者を検知！】（全{count}件）\n"]

    for i, item in enumerate(targets[:MAX_NOTIFY_COUNT], 1):
        msg_lines.append("━" * 15)
        msg_lines.append(f"【{i}件目】")
        msg_lines.append(f"🕒 日時: {item['created_at']}")
        msg_lines.append(f"📝 投稿:\n{item['text']}")
        msg_lines.append(f"💡 理由: {item['reason']}")
        msg_lines.append(f"🔗 リンク:\n{item['url']}\n")

    if count > MAX_NOTIFY_COUNT:
        msg_lines.append(f"⚠️ 件数が多いため、上位{MAX_NOTIFY_COUNT}件のみ表示しました。")

    full_message = "\n".join(msg_lines)

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": full_message}]
    }
    res = requests.post(url, headers=headers, json=data)
    if res.status_code == 200:
        print("✅ LINE通知を送信しました！")
    else:
        print(f"❌ LINE送信エラー ({res.status_code}): {res.text}")

def main():
    last_id = get_last_id()
    print(f"📖 前回のしおりID: {last_id}")

    tweets = search_tweets(since_id=last_id)
    if not tweets:
        print("✨ 新着投稿はありませんでした。終了します。")
        return

    # 一番新しい投稿IDを記憶
    newest_id = tweets[0]["id"]
    targets = []

    # 古い順にAI判定
    for tweet in reversed(tweets):
        tweet_id = tweet["id"]
        text = tweet["text"]
        created_at = tweet.get("created_at", "")
        tweet_url = f"https://x.com/i/web/status/{tweet_id}"

        print(f"\n--- 検証中: {tweet_url} ---")
        is_target, reason = judge_with_ai(text)

        if is_target:
            print(f"🔔 アプローチ対象を発見！ (理由: {reason})")
            targets.append({
                "text": text,
                "url": tweet_url,
                "reason": reason,
                "created_at": created_at
            })
        else:
            print(f"⏩ 対象外: {reason}")

    # 該当があれば1通にまとめてLINE送信
    if targets:
        send_combined_line(targets)

    # しおりを更新
    save_last_id(newest_id)
    print(f"\n✅ しおりを更新しました: {newest_id}")

if __name__ == "__main__":
    main()
