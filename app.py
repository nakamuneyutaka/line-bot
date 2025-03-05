import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# 環境変数からトークンとAPIキーを取得
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot with GPT is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Received:", data)  # ログにデータを出力

    # イベントが含まれているかチェック
    if "events" in data:
        for event in data["events"]:
            if event["type"] == "message" and "text" in event["message"]:
                reply_token = event["replyToken"]
                user_message = event["message"]["text"]

                # 🔹 OpenAI API を使って返信を生成
                reply_text = generate_gpt_response(user_message)

                # 🔹 LINEに返信を送信
                send_line_reply(reply_token, reply_text)

    return jsonify({"status": "ok"})

def generate_gpt_response(user_message):
    """OpenAI API を使ってメッセージを生成（カスタムGPT対応版）"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    data = {
        "model": "gpt-4-turbo",  # 🔹 クリエイトGPTを使う
        "messages": [{"role": "user", "content": user_message}],
        "tool_choice": "auto"  # 🔹 カスタムGPTのツールを自動選択
    }
    response = requests.post(url, json=data, headers=headers)
    result = response.json()

    # 🔹 OpenAI APIのレスポンスをログに出力（デバッグ用）
    print("OpenAI API Response:", result)

    # APIのレスポンスを解析して返信テキストを取得
    return result.get("choices", [{}])[0].get("message", {}).get("content", "エラーが発生しました。")

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
