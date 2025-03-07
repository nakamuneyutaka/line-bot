def generate_gpt_response(user_message):
    """OpenAI API を使ってGPT-4 Turboのメッセージを生成"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    data = {
        "model": "gpt-4-turbo",
        "messages": [{"role": "user", "content": user_message}]
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        result = response.json()

        # OpenAI APIのレスポンスを詳細にログに出力
        print("🔍 OpenAI API Response:", result)

        # エラーがある場合はログに出してエラーメッセージを返す
        if "error" in result:
            return f"⚠️ OpenAI API エラー: {result['error']['message']}"

        # APIのレスポンスを解析して返信テキストを取得
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            return "エラー: GPTの応答がありません。"

    except Exception as e:
        print("⚠️ OpenAI API 呼び出し中にエラー:", e)
        return "エラー: GPTの通信に失敗しました。"
