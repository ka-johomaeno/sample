from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    QuickReply, QuickReplyButton, MessageAction
)
import json
import os

app = Flask(__name__)

# 環境変数（Renderなどに設定する）
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 先生データを読み込む
with open("teachers.json", "r", encoding="utf-8") as f:
    TEACHERS = json.load(f)

# ユーザーごとの状態を記録
user_state = {}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text.strip()

    # スタート
    if user_msg in ["スタート", "こんにちは", "はじめる"]:
        categories = list(TEACHERS.keys())
        buttons = [QuickReplyButton(action=MessageAction(label=c, text=c)) for c in categories]
        msg = TextSendMessage(
            text="どんな悩みがありますか？",
            quick_reply=QuickReply(items=buttons)
        )
        user_state[user_id] = {"step": "choose_category"}
        line_bot_api.reply_message(event.reply_token, msg)
        return

    # カテゴリ選択後
    if user_id in user_state and user_state[user_id].get("step") == "choose_category":
        if user_msg in TEACHERS:
            subkeys = list(TEACHERS[user_msg].keys())
            buttons = [QuickReplyButton(action=MessageAction(label=s, text=s)) for s in subkeys]
            msg = TextSendMessage(
                text=f"{user_msg}について、もう少し詳しく教えてください👇",
                quick_reply=QuickReply(items=buttons)
            )
            user_state[user_id] = {"step": "choose_detail", "category": user_msg}
            line_bot_api.reply_message(event.reply_token, msg)
            return
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="もう一度選んでください。"))
            return

    # 詳細選択後
    if user_id in user_state and user_state[user_id].get("step") == "choose_detail":
        category = user_state[user_id]["category"]
        if user_msg in TEACHERS[category]:
            teacher = TEACHERS[category][user_msg]
            msg = TextSendMessage(
                text=f"おすすめの先生は「{teacher['name']}」です！\n{teacher['desc']}"
            )
            user_state[user_id] = {}
            line_bot_api.reply_message(event.reply_token, msg)
            return
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="もう一度選んでください。"))
            return

    # それ以外
    msg = TextSendMessage(text="「スタート」と入力して相談を始めましょう！")
    line_bot_api.reply_message(event.reply_token, msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

