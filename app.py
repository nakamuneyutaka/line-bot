import time
import requests
from flask import current_app

# OpenAI API のヘッダー（環境変数から取得している前提）
HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
    "OpenAI-Beta": "assistants=v2"
}

def generate_gpt_response(user_message):
    """Assistants API を使ってカスタムGPTのメッセージを生成"""
    try:
        with current_app.app_context():  # Flaskのコンテキストを確保
            current_app.logger.info("🔹 スレッド作成開始")
            thread_response = requests.post("https://api.openai.com/v1/threads", headers=HEADERS, json={})

            if not thread_response.ok:
                current_app.logger.error(f"❌ スレッド作成エラー: {thread_response.status_code}, {thread_response.text}")
                return "スレッド作成でエラーが発生しました。"

            thread_data = thread_response.json()
            thread_id = thread_data.get("id")
            if not thread_id:
                current_app.logger.error(f"❌ スレッドIDが取得できません: {thread_data}")
                return "スレッドIDの取得に失敗しました。"

            current_app.logger.info(f"✅ スレッド作成成功: {thread_id}")

            current_app.logger.info("🔹 メッセージ追加開始")
            message_response = requests.post(
                f"https://api.openai.com/v1/threads/{thread_id}/messages",
                headers=HEADERS,
                json={"role": "user", "content": user_message}
            )

            if not message_response.ok:
                current_app.logger.error(f"❌ メッセージ追加エラー: {message_response.status_code}, {message_response.text}")
                return "メッセージ追加でエラーが発生しました。"

            current_app.logger.info("🔹 アシスタント実行開始")
            run_response = requests.post(
                f"https://api.openai.com/v1/threads/{thread_id}/runs",
                headers=HEADERS,
                json={"assistant_id": ASSISTANT_ID}
            )

            if not run_response.ok:
                current_app.logger.error(f"❌ アシスタント実行エラー: {run_response.status_code}, {run_response.text}")
                return "アシスタント実行でエラーが発生しました。"

            run_data = run_response.json()
            run_id = run_data.get("id")
            if not run_id:
                current_app.logger.error(f"❌ Run IDが取得できません: {run_data}")
                return "Run IDの取得に失敗しました。"

            current_app.logger.info(f"✅ アシスタント実行成功: {run_id}")

            # アシスタントの実行状態をポーリング（最大10秒）
            for _ in range(5):
                time.sleep(2)
                current_app.logger.info("🔹 Run ステータス取得開始")
                run_status_response = requests.get(
                    f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}",
                    headers=HEADERS
                )

                if not run_status_response.ok:
                    current_app.logger.error(f"❌ Run ステータス取得エラー: {run_status_response.status_code}, {run_status_response.text}")
                    return "Run ステータス取得でエラーが発生しました。"

                run_status = run_status_response.json().get("status")
                current_app.logger.info(f"🔹 Run ステータス: {run_status}")

                if run_status == "completed":
                    break  # 実行完了なら次へ
                elif run_status in ["failed", "cancelled"]:
                    current_app.logger.error(f"❌ Run が失敗またはキャンセルされました: {run_status_response.json()}")
                    return "アシスタント実行が失敗またはキャンセルされました。"

            current_app.logger.info("🔹 メッセージ取得開始")
            response = requests.get(
                f"https://api.openai.com/v1/threads/{thread_id}/messages",
                headers=HEADERS
            )

            if not response.ok:
                current_app.logger.error(f"❌ メッセージ取得エラー: {response.status_code}, {response.text}")
                return "メッセージ取得でエラーが発生しました。"

            messages = response.json().get("messages", [])
            if not messages:
                current_app.logger.error("❌ 取得したメッセージが空です。")
                return "AIからのレスポンスがありませんでした。"

            # メッセージの最後のレスポンスを取得
            last_message = messages[-1].get("content")
            if isinstance(last_message, list) and last_message:
                if isinstance(last_message[0], dict) and "text" in last_message[0]:
                    return last_message[0]["text"]
                return "メッセージ解析エラーが発生しました。"
            elif isinstance(last_message, str):
                return last_message  # 直接テキストとして返す場合

            return "予期しないエラーが発生しました。"

    except Exception as e:
        current_app.logger.error(f"⚠️ OpenAI API 呼び出し中にエラー: {e}")
        return "システムエラーが発生しました。"
