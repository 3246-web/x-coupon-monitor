import os
import requests
import json
import time

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 試すモデルの候補（混雑時は次のモデルを自動で試す）
MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash"]

PROMPT_TEMPLATE = """
以下のSNSの投稿本文を読み、投稿者が「品川近視クリニックの紹介・割引クーポン・紹介コードを求めている（探している・使いたい）」かどうかを判定してください。

【判定基準】
- 投稿者がクーポンや紹介を求めている、探している、欲しいと言っている場合は「YES」
- 既に受けた感想、自分が紹介を配っている側、無関係な話題の場合は「NO」

回答は必ず以下のJSON形式のみで出力してください（マークダウンや追加の解説は不要です）：
{{"is_target": true, "reason": "判定理由を日本語で簡潔に"}}
または
{{"is_target": false, "reason": "判定理由を日本語で簡潔に"}}

【投稿本文】
{text}
"""

def judge_post(post_text):
    prompt = PROMPT_TEMPLATE.format(text=post_text)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    # モデルを順番に試す
    for model_id in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
        
        for retry in range(2): # 混雑時は最大2回リトライ
            res = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                params={"key": GEMINI_API_KEY},
                json=payload
            )
            
            if res.status_code == 200:
                result_text = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                # 余計な ```json などの囲み文字を削除
                result_text = result_text.replace("```json", "").replace("```", "").strip()
                return result_text, model_id
            elif res.status_code == 503:
                print(f"⚠️ {model_id} が混雑中(503)。3秒待機して再試行します...")
                time.sleep(3)
            else:
                print(f"❌ エラー ({model_id}, ステータス {res.status_code}): {res.text}")
                break
                
    return None, None

test_posts = [
    "品川近視クリニックでレーシック受けようか迷ってるんだけど、紹介コードとか割引クーポン持ってる人いませんか？？",
    "品川近視クリニックでレーシック手術受けてきた！視界良好で本当に人生変わったわ"
]

print("🤖 Gemini AI判定テストを開始します...\n")

for i, post in enumerate(test_posts, 1):
    print(f"--- テスト{i} ---")
    print(f"投稿本文: {post}")
    
    result, used_model = judge_post(post)
    if result:
        print(f"AIの回答 ({used_model}が回答): {result}\n")
    else:
        print("❌ 全てのモデルで判定に失敗しました。\n")
