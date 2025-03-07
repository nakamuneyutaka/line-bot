import os
import time
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 環境変数をロード
load_dotenv()

# 環境変数から LINE の設定を取得
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# LINE Bot API & Webhook ハンドラーを設定
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Flask アプリの作成
app = Flask(__name__)

# ロギング設定
import logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

@app.route('/')
def home():
    return "Flask LINE Bot API Server is running!"

@app.route('/chat', methods=['POST'])
def chat():
    """API エンドポイント: カスタムGPTでメッセージを生成"""
    user_message = request.json.get("message", "")
    if not user_message:
        return jsonify({"error": "メッセージが空です"}), 400
    
    response = generate_gpt_response(user_message)
    return jsonify({"response": response})

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """LINE の Webhook エンドポイント"""
    if request.method == 'GET':
        return "Webhook is running", 200  # Webhook の動作確認用

    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    if not signature:
        app.logger.error("❌ LINE Webhook の署名がありません")
        return jsonify({"error": "Missing X-Line-Signature"}), 400

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("❌ LINE Webhook の署名検証に失敗しました")
        return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        app.logger.error(f"⚠️ Webhook 処理中にエラー: {e}")
        return jsonify({"error": "Webhook processing failed"}), 500

    return "OK", 200

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """LINE からメッセージを受信し、OpenAI に渡して返信"""
    user_message = event.message.text
    app.logger.info(f"📩 LINE からのメッセージ: {user_message}")
    
    ai_response = generate_gpt_response(user_message)
    
    if not ai_response:
        ai_response = "ごめんなさい、うまく応答できませんでした。"

    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_response)
        )
        app.logger.info(f"📤 AI の返信: {ai_response}")
    except Exception as e:
        app.logger.error(f"⚠️ LINE への返信エラー: {e}")

def generate_gpt_response(user_message):
    """OpenAI Assistants API を使って AI のメッセージを取得"""
    try:
        HEADERS = {
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            "Content-Type": "application/json",
            "OpenAI-Beta": "assistants=v2"
        }

        app.logger.info("🔹 スレッド作成開始")
        thread_response = requests.post("https://api.openai.com/v1/threads", headers=HEADERS, json={})

        if not thread_response.ok:
            app.logger.error(f"❌ スレッド作成エラー: {thread_response.status_code}, {thread_response.text}")
            return "エラーが発生しました。"

        thread_id = thread_response.json().get("id")
        if not thread_id:
            return "スレッド ID の取得に失敗しました。"

        app.logger.info(f"✅ スレッド作成成功: {thread_id}")

        app.logger.info("🔹 メッセージ追加開始")
        requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/messages",
            headers=HEADERS,
            json={"role": "user", "content": user_message}
        )

        app.logger.info("🔹 アシスタント実行開始")
        run_response = requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/runs",
            headers=HEADERS,
            json={"assistant_id": os.getenv("ASSISTANT_ID")}
        )

        if not run_response.ok:
            return "AI 実行エラー"

        run_id = run_response.json().get("id")
        if not run_id:
            return "Run ID の取得に失敗しました。"

        # AI のレスポンスを取得
        time.sleep(3)
        response = requests.get(
            f"https://api.openai.com/v1/threads/{thread_id}/messages",
            headers=HEADERS
        )

        if not response.ok:
            return "メッセージ取得エラー"

        messages = response.json().get("data", [])
        assistant_message = next((msg for msg in messages if msg["role"] == "assistant"), None)

        if assistant_message:
            for content in assistant_message["content"]:
                if content["type"] == "text":
                    return content["text"]["value"]

        return "AI の応答がありませんでした。"

    except Exception as e:
        app.logger.error(f"⚠️ OpenAI API 呼び出し中にエラー: {e}")
        return "システムエラーが発生しました。"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
