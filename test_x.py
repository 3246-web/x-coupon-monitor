import os
import requests
import json

BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN")

# X APIの検索URL
url = "https://api.twitter.com/2/tweets/search/recent"

# 検索条件：リツイートを除外し、日本語の投稿を検索
query = "品川近視 -is:retweet lang:ja"

params = {
    "query": query,
    "max_results": 10, # 最小設定の10件
    "tweet.fields": "created_at,text,author_id"
}

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}"
}

print(f"🔍 X（Twitter）で検索を実行中... キーワード: [{query}]\n")

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    tweets = data.get("data", [])
    count = data.get("meta", {}).get("result_count", 0)
    
    print(f"✅ 取得成功！ ヒット件数: {count} 件\n")
    
    for i, tweet in enumerate(tweets, 1):
        tweet_id = tweet.get("id")
        created_at = tweet.get("created_at")
        text = tweet.get("text").replace("\n", " ") # 1行でスッキリ表示
        url = f"https://x.com/i/web/status/{tweet_id}"
        
        print(f"[{i}] 日時: {created_at}")
        print(f"    本文: {text[:60]}...") # 冒頭60文字
        print(f"    URL: {url}\n")
        
    if count == 0:
        print("※直近数日間に該当する投稿がありませんでした。接続自体は正常です！")
else:
    print(f"❌ エラーが発生しました (ステータス {response.status_code}):")
    print(response.text)
