import os
import requests
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# 環境変数からトークンとAPIキーを取得
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")  # カスタムGPT（Assistant）のID

# 環境変数の確認
if not OPENAI_API_KEY:
    app.logger.warning("⚠️ OPENAI_API_KEY が設定されていません！")
if not LINE_ACCESS_TOKEN:
    app.logger.warning("⚠️ LINE_ACCESS_TOKEN が設定されていません！")
if not ASSISTANT_ID:
    app.logger.warning("⚠️ ASSISTANT_ID が設定されていません！")

# OpenAI API の共通ヘッダー
HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
    "OpenAI-Beta": "assistants=v2"  # Assistants API v2 のヘッダーを追加
}

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot with Custom GPT is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    """LINEからのWebhookを受信して処理"""
    data = request.get_json(force=True)
    app.logger.info(f"Received: {data}")

    if not data or "events" not in data:
        app.logger.warning("⚠️ Webhook に events データが含まれていません！")
        return jsonify({"status": "error", "message": "Invalid request"}), 400

    for event in data["events"]:
        reply_token = event.get("replyToken")
        user_message = event.get("message", {}).get("text", "")

        if not reply_token or not user_message:
            app.logger.warning(f"⚠️ Warning: 必要なデータが不足: {event}")
            continue

        # 🔹 カスタムGPT（Assistants API）を使って返信を生成
        reply_text = generate_gpt_response(user_message)

        # 🔹 LINEに返信を送信
        send_line_reply(reply_token, reply_text)

    return jsonify({"status": "ok"})

def generate_gpt_response(user_message):
    """Assistants API を使ってカスタムGPTのメッセージを生成"""
    try:
        # 1. スレッドを作成
        thread_response = requests.post("https://api.openai.com/v1/threads", headers=HEADERS, json={})
        if thread_response.status_code != 200:
            app.logger.error(f"❌ スレッド作成エラー: {thread_response.status_code}, {thread_response.text}")
            return "エラーが発生しました。"

        thread_id = thread_response.json().get("id")
        app.logger.info(f"✅ スレッド作成成功: {thread_id}")

        # 2. スレッドにメッセージを追加
        message_response = requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/messages",
            headers=HEADERS,
            json={"role": "user", "content": user_message}
        )
        if message_response.status_code != 200:
            app.logger.error(f"❌ メッセージ追加エラー: {message_response.status_code}, {message_response.text}")
            return "エラーが発生しました。"

        # 3. アシスタントを実行
        run_response = requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/runs",
            headers=HEADERS,
            json={"assistant_id": ASSISTANT_ID}
        )
        if run_response.status_code != 200:
            app.logger.error(f"❌ アシスタント実行エラー: {run_response.status_code}, {run_response.text}")
            return "エラーが発生しました。"

        run_id = run_response.json().get("id")
        app.logger.info(f"✅ アシスタント実行成功: {run_id}")

        # 4. 結果が返るまでポーリング（最大3回）
        for _ in range(3):
            time.sleep(2)
            response = requests.get(
                f"https://api.openai.com/v1/threads/{thread_id}/messages",
                headers=HEADERS
            )
            if response.status_code != 200:
                app.logger.error(f"❌ メッセージ取得エラー: {response.status_code}, {response.text}")
                return "エラーが発生しました。"

            messages = response.json().get("messages", [])
            if messages:
                return messages[-1].get("content", "エラーが発生しました。")

        return "エラーが発生しました。"

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
        app.logger.info(f"LINE API Response: {response.status_code}, {response.json()}")

        if response.status_code != 200:
            app.logger.error(f"❌ LINE API エラー: {response.status_code}, {response.text}")

    except Exception as e:
        app.logger.error(f"⚠️ LINE API 呼び出し中にエラー: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
