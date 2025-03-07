def generate_gpt_response(user_message):
    """Assistants API を使ってカスタムGPTのメッセージを生成"""
    try:
        print("🔹 スレッド作成開始")
        thread_response = requests.post("https://api.openai.com/v1/threads", headers=HEADERS, json={})

        if not thread_response.ok:
            app.logger.error(f"❌ スレッド作成エラー: {thread_response.status_code}, {thread_response.text}")
            return "エラーが発生しました。"

        thread_data = thread_response.json()
        thread_id = thread_data.get("id")
        if not thread_id:
            app.logger.error(f"❌ スレッドIDが取得できません: {thread_data}")
            return "エラーが発生しました。"

        print(f"✅ スレッド作成成功: {thread_id}")

        print("🔹 メッセージ追加開始")
        message_response = requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/messages",
            headers=HEADERS,
            json={"role": "user", "content": user_message}
        )

        if not message_response.ok:
            app.logger.error(f"❌ メッセージ追加エラー: {message_response.status_code}, {message_response.text}")
            return "エラーが発生しました。"

        print("🔹 アシスタント実行開始")
        run_response = requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/runs",
            headers=HEADERS,
            json={"assistant_id": ASSISTANT_ID}
        )

        if not run_response.ok:
            app.logger.error(f"❌ アシスタント実行エラー: {run_response.status_code}, {run_response.text}")
            return "エラーが発生しました。"

        run_data = run_response.json()
        run_id = run_data.get("id")
        if not run_id:
            app.logger.error(f"❌ Run IDが取得できません: {run_data}")
            return "エラーが発生しました。"

        print(f"✅ アシスタント実行成功: {run_id}")

        # アシスタントの実行状態をポーリング（最大10秒）
        for _ in range(5):
            time.sleep(2)
            print("🔹 Run ステータス取得開始")
            run_status_response = requests.get(
                f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}",
                headers=HEADERS
            )

            if not run_status_response.ok:
                app.logger.error(f"❌ Run ステータス取得エラー: {run_status_response.status_code}, {run_status_response.text}")
                return "エラーが発生しました。"

            run_status = run_status_response.json().get("status")
            print(f"🔹 Run ステータス: {run_status}")

            if run_status == "completed":
                break  # 実行完了なら次へ
            elif run_status in ["failed", "cancelled"]:
                app.logger.error(f"❌ Run が失敗またはキャンセルされました: {run_status_response.json()}")
                return "エラーが発生しました。"

        print("🔹 メッセージ取得開始")
        response = requests.get(
            f"https://api.openai.com/v1/threads/{thread_id}/messages",
            headers=HEADERS
        )

        if not response.ok:
            app.logger.error(f"❌ メッセージ取得エラー: {response.status_code}, {response.text}")
            return "エラーが発生しました。"

        messages = response.json().get("messages", [])
        if not messages:
            app.logger.error("❌ 取得したメッセージが空です。")
            return "エラーが発生しました。"

        # メッセージの最後のレスポンスを取得
        last_message = messages[-1].get("content")
        if isinstance(last_message, list) and last_message:
            return last_message[0].get("text", "エラーが発生しました。")  # `text` の中身を取得
        elif isinstance(last_message, str):
            return last_message  # 直接テキストとして返す場合

        return "エラーが発生しました。"

    except Exception as e:
        app.logger.error(f"⚠️ OpenAI API 呼び出し中にエラー: {e}")
        return "エラーが発生しました。"
