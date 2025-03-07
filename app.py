import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# 環境変数からトークンとAPIキーを取得
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 環境変数の確認をログに出力（デバッグ用）
if not OPENAI_API_KEY:
    app.logger.warning("⚠️ OPENAI_API_KEY が設定されていません！")

if not LINE_ACCESS_TOKEN:
    app.logger.warning("⚠️ LINE_ACCESS_TOKEN が設定されていません！")

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot with GPT is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    """LINEからのWebhookを受信して処理"""
    data = request.get_json(force=True)  # force=TrueでJSONパースエラーを防ぐ
    app.logger.info(f"Received: {data}")  # ログにデータを出力（デバッグ用）

    if not data or "events" not in data:
        app.logger.warning("⚠️ Webhook に events データが含まれていません！")
        return jsonify({"status": "error", "message": "Invalid request"}), 400

    for event in data["events"]:
        reply_token = event.get("replyToken")
        user_message = event.get("message", {}).get("text", "")

        if not reply_token:
            app.logger.warning(f"⚠️ Warning: replyToken が見つかりません。イベントデータ: {event}")
            continue

        if not user_message:
            app.logger.warning(f"⚠️ Warning: メッセージが見つかりません。イベントデータ: {event}")
            continue

        # 🔹 OpenAI API を使って返信を生成
        reply_text = generate_gpt_response(user_message)

        # 🔹 LINEに返信を送信
        send_line_reply(reply_token, reply_text)

    return jsonify({"status": "ok"})

def generate_gpt_response(user_message):
    """OpenAI API を使ってカスタムGPTのメッセージを生成"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    data = {
        "model": "gpt-4-turbo",  # ✅ `custom_gpt_id` を削除し、モデル名のみ指定
        "messages": [{"role": "user", "content": user_message}]
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        
        # HTTP ステータスコードをチェック
        if response.status_code != 200:
            app.logger.error(f"❌ OpenAI API エラー: {response.status_code}, {response.text}")
            return "エラーが発生しました。"

        result = response.json()
        app.logger.info(f"OpenAI API Response: {result}")  # 🔹 レスポンスをログに出力

        return result.get("choices", [{}])[0].get("message", {}).get("content", "エラーが発生しました。")

    except Exception as e:
        app.logger.error(f"⚠️ OpenAI API 呼び出し中にエラー: {e}")
        return "エラーが発生しました。"

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

    try:
        response = requests.post(url, json=data, headers=headers)
        app.logger.info(f"LINE API Response: {response.status_code}, {response.json()}")  # 🔹 ステータスコードもログに出力

        if response.status_code != 200:
            app.logger.error(f"❌ LINE API エラー: {response.status_code}, {response.text}")

    except Exception as e:
        app.logger.error(f"⚠️ LINE API 呼び出し中にエラー: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
