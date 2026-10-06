import os
import requests

# GitHub Secretsからキーを読み込む
TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.environ.get("LINE_USER_ID")

url = "https://api.line.me/v2/bot/message/push"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}
data = {
    "to": USER_ID,
    "messages": [
        {
            "type": "text",
            "text": "🎉 LINE通知のテスト送信に成功しました！\nシステムは正常に接続されています。"
        }
    ]
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    print("✅ 送信成功！LINEを確認してください。")
else:
    print(f"❌ 送信失敗: ステータスコード {response.status_code}")
    print(response.text)
