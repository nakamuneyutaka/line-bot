import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# 🔹 アクセストークンを環境変数から取得する（セキュリティ対策！）
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Received:", data)  # 受け取ったデータをログに表示

    # イベントが含まれているかチェック
    if "events" in data:
        for event in data["events"]:
            if event["type"] == "message" and "text" in event["message"]:
                reply_token = event["replyToken"]
                user_message = event["message"]["text"]
                reply_text = f"あなたは「{user_message}」と言いましたね！"
                send_line_reply(reply_token, reply_text)

    return jsonify({"status": "ok"})

def send_line_reply(reply_token, text):
    """LINEに返信を送る関数"""
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post(url, json=data, headers=headers)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
