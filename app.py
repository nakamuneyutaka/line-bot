import os
import time
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# 環境変数をロード
load_dotenv()

# OpenAI APIキーを環境変数から取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

if not OPENAI_API_KEY:
    raise ValueError("❌ 環境変数 'OPENAI_API_KEY' が設定されていません。")

if not ASSISTANT_ID:
    raise ValueError("❌ 環境変数 'ASSISTANT_ID' が設定されていません。")

# Flask アプリの作成
app = Flask(__name__)

# ロギング設定
import logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

@app.route('/')
def home():
    return "Flask OpenAI API Server is running!"

@app.route('/chat', methods=['POST'])
def chat():
    """API エンドポイント: カスタムGPTでメッセージを生成"""
    user_message = request.json.get("message", "")
    if not user_message:
        return jsonify({"error": "メッセージが空です"}), 400
    
    response = generate_gpt_response(user_message)
    app.logger.info(f"🔹 最終レスポンス: {response}")  # 最後にログを出す
    return jsonify({"response": response})

def generate_gpt_response(user_message):
    """Assistants API を使ってカスタムGPTのメッセージを生成"""
    try:
        HEADERS = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
            "OpenAI-Beta": "assistants=v2"
        }

        app.logger.info("🔹 スレッド作成開始")
        thread_response = requests.post("https://api.openai.com/v1/threads", headers=HEADERS, json={})

        if not thread_response.ok:
            app.logger.error(f"❌ スレッド作成エラー: {thread_response.status_code}, {thread_response.text}")
            return "スレッド作成でエラーが発生しました。"

        thread_data = thread_response.json()
        thread_id = thread_data.get("id")
        if not thread_id:
            app.logger.error(f"❌ スレッドIDが取得できません: {thread_data}")
            return "スレッドIDの取得に失敗しました。"

        app.logger.info(f"✅ スレッド作成成功: {thread_id}")

        app.logger.info("🔹 メッセージ追加開始")
        message_response = requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/messages",
            headers=HEADERS,
            json={"role": "user", "content": user_message}
        )

        if not message_response.ok:
            app.logger.error(f"❌ メッセージ追加エラー: {message_response.status_code}, {message_response.text}")
            return "メッセージ追加でエラーが発生しました。"

        app.logger.info("🔹 アシスタント実行開始")
        run_response = requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/runs",
            headers=HEADERS,
            json={"assistant_id": ASSISTANT_ID}
        )

        if not run_response.ok:
            app.logger.error(f"❌ アシスタント実行エラー: {run_response.status_code}, {run_response.text}")
            return "アシスタント実行でエラーが発生しました。"

        run_data = run_response.json()
        run_id = run_data.get("id")
        if not run_id:
            app.logger.error(f"❌ Run IDが取得できません: {run_data}")
            return "Run IDの取得に失敗しました。"

        app.logger.info(f"✅ アシスタント実行成功: {run_id}")

        # アシスタントの実行状態をポーリング（最大10秒）
        for _ in range(5):
            time.sleep(2)
            app.logger.info("🔹 Run ステータス取得開始")
            run_status_response = requests.get(
                f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}",
                headers=HEADERS
            )

            if not run_status_response.ok:
                app.logger.error(f"❌ Run ステータス取得エラー: {run_status_response.status_code}, {run_status_response.text}")
                return "Run ステータス取得でエラーが発生しました。"

            run_status = run_status_response.json().get("status")
            app.logger.info(f"🔹 Run ステータス: {run_status}")

            if run_status == "completed":
                break  # 実行完了なら次へ
            elif run_status in ["failed", "cancelled"]:
                app.logger.error(f"❌ Run が失敗またはキャンセルされました: {run_status_response.json()}")
                return "アシスタント実行が失敗またはキャンセルされました。"

        app.logger.info("🔹 メッセージ取得開始")
        response = requests.get(
            f"https://api.openai.com/v1/threads/{thread_id}/messages",
            headers=HEADERS
        )

        if not response.ok:
            app.logger.error(f"❌ メッセージ取得エラー: {response.status_code}, {response.text}")
            return "メッセージ取得でエラーが発生しました。"

        response_json = response.json()
        app.logger.info(f"🔹 OpenAI API レスポンス: {response_json}")  # ここで詳細なログを出力

        messages = response_json.get("messages", [])
        if not messages:
            app.logger.error("❌ 取得したメッセージが空です。")
            return "AIからのレスポンスがありませんでした。"

        # メッセージの最後のレスポンスを取得
        last_message = messages[-1].get("content")
        if isinstance(last_message, list) and last_message:
            if isinstance(last_message[0], dict) and "text" in last_message[0]:
                app.logger.info(f"✅ AI からの最終メッセージ: {last_message[0]['text']}")
                return last_message[0]["text"]
            app.logger.error("❌ メッセージ解析エラー")
            return "メッセージ解析エラーが発生しました。"
        elif isinstance(last_message, str):
            app.logger.info(f"✅ AI からの最終メッセージ: {last_message}")
            return last_message  # 直接テキストとして返す場合

        app.logger.error("❌ 予期しないエラーが発生しました。")
        return "予期しないエラーが発生しました。"

    except Exception as e:
        app.logger.error(f"⚠️ OpenAI API 呼び出し中にエラー: {e}")
        return "システムエラーが発生しました。"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
