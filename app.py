def generate_gpt_response(user_message):
    """Assistants API を使ってカスタムGPTのメッセージを生成"""
    try:
        print("🔹 スレッド作成開始")
        thread_response = requests.post("https://api.openai.com/v1/threads", headers=HEADERS, json={})
        print(f"🔹 スレッド作成レスポンス: {thread_response.status_code}, {thread_response.text}")
        
        if thread_response.status_code != 200:
            app.logger.error(f"❌ スレッド作成エラー: {thread_response.status_code}, {thread_response.text}")
            return "エラーが発生しました。"

        thread_id = thread_response.json().get("id")
        print(f"✅ スレッド作成成功: {thread_id}")

        print("🔹 メッセージ追加開始")
        message_response = requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/messages",
            headers=HEADERS,
            json={"role": "user", "content": user_message}
        )
        print(f"🔹 メッセージ追加レスポンス: {message_response.status_code}, {message_response.text}")
        
        if message_response.status_code != 200:
            app.logger.error(f"❌ メッセージ追加エラー: {message_response.status_code}, {message_response.text}")
            return "エラーが発生しました。"

        print("🔹 アシスタント実行開始")
        run_response = requests.post(
            f"https://api.openai.com/v1/threads/{thread_id}/runs",
            headers=HEADERS,
            json={"assistant_id": ASSISTANT_ID}
        )
        print(f"🔹 アシスタント実行レスポンス: {run_response.status_code}, {run_response.text}")
        
        if run_response.status_code != 200:
            app.logger.error(f"❌ アシスタント実行エラー: {run_response.status_code}, {run_response.text}")
            return "エラーが発生しました。"

        run_id = run_response.json().get("id")
        print(f"✅ アシスタント実行成功: {run_id}")

        for _ in range(3):
            time.sleep(2)
            print("🔹 レスポンス取得開始")
            response = requests.get(
                f"https://api.openai.com/v1/threads/{thread_id}/messages",
                headers=HEADERS
            )
            print(f"🔹 レスポンス取得レスポンス: {response.status_code}, {response.text}")

            if response.status_code != 200:
                app.logger.error(f"❌ メッセージ取得エラー: {response.status_code}, {response.text}")
                return "エラーが発生しました。"

            messages = response.json().get("messages", [])
            if messages:
                return messages[-1]["content"]

        return "エラーが発生しました。"

    except Exception as e:
        app.logger.error(f"⚠️ OpenAI API 呼び出し中にエラー: {e}")
        return "エラーが発生しました。"
