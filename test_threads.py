import os
import requests
import json

APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN")

# ApifyでThreadsを検索するActor（ロボット）のエンドポイント
# run-sync-get-dataset-items を使うと、検索が終わるまで待って結果をまとめて返してくれます
url = "https://api.apify.com/v2/acts/burbn~threads-search-scraper/run-sync-get-dataset-items"

payload = {
    "searchQueries": ["品川近視"],
    "maxPosts": 5,          # テストなので最小限の5件
    "searchSort": "recent"  # 最新順
}

headers = {"Content-Type": "application/json"}
params = {"token": APIFY_TOKEN}

print("🔍 Apifyを使ってThreadsの投稿を検索中...（約20〜30秒かかります）\n")

response = requests.post(url, headers=headers, params=params, json=payload, timeout=120)

if response.status_code in [200, 201]:
    items = response.json()
    print(f"✅ 取得成功！ 件数: {len(items)} 件\n")
    
    for i, item in enumerate(items, 1):
        # Threadsのデータ構造から本文とURLを取り出す
        text = item.get("text") or item.get("caption") or "(本文なし)"
        post_url = item.get("url") or item.get("postUrl") or "(URLなし)"
        created_at = item.get("publishedAt") or item.get("createdAt") or "(日時不明)"
        
        # 1行で綺麗に表示
        clean_text = text.replace("\n", " ")[:60]
        print(f"[{i}] 日時: {created_at}")
        print(f"    本文: {clean_text}...")
        print(f"    URL: {post_url}\n")
        
    if len(items) == 0:
        print("※直近で該当する投稿が見つかりませんでした。")
else:
    print(f"❌ エラーが発生しました (ステータス {response.status_code}):")
    print(response.text)
