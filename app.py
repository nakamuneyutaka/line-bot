import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# 環境変数からトークンとAPIキーを取得
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# APIキーの存在をチェック（デバッグ用）
if not OPENAI_API_KEY:
    print("⚠️ OPENAI_API_KEY が設定されていません！")

if not LINE_ACCESS_TOKEN:
    print("⚠️ LINE_ACCESS_TOKEN が設定されていません！")

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot with GPT is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Received:", data)  # ログにデータを出力（デバッグ用）

    # イベントが含まれているかチェック
    if "events" in data:
        for event in data["events"]:
            reply_token = event.get("replyToken")  # replyTokenがない場合Noneを返す
            user_message = event.get("message", {}).get("text", "")

            if not reply_token:
                print("⚠️ Warning: replyTokenが見つかりません。スキップします。イベントデータ:", event)
                continue  # エラーにせずスキップ

            if not user_message:
                print("⚠️ Warning: メッセージが見つかりません。スキップします。イベントデータ:", event)
                continue  # エラーにせずスキップ

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
        "model": "g-67c0fb788848819195db91164e464600",  # 🔹 カスタムGPTのIDを指定
        "messages": [{"role": "user", "content": user_message}]
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        result = response.json()

        # 🔹 OpenAI APIのレスポンスをログに出力（デバッグ用）
        print("OpenAI API Response:", result)

        if "error" in result:
            print("⚠️ OpenAI API エラー:", result["error"])
            return f"⚠️ エラー: {result['error'].get('message', '不明なエラー')}"

        # APIのレスポンスを解析して返信テキストを取得
        return result.get("choices", [{}])[0].get("message", {}).get("content", "エラーが発生しました。")

    except Exception as e:
        print("⚠️ OpenAI API 呼び出し中にエラー:", e)
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
        response_json = response.json()
        print("LINE API Response:", response_json)  # 🔹 レスポンスをログに出力

        if response.status_code != 200:
            print("⚠️ LINE API エラー:", response_json)  # エラー内容をログに出力

    except Exception as e:
        print("⚠️ LINE API 呼び出し中にエラー:", e)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
