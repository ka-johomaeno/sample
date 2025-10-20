from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction
import os
import json

app = Flask(__name__)

# 環境変数から取得（Renderで設定）
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- JSONファイルから教員データをロード ---
with open("teachers.json", "r", encoding="utf-8") as f:
    teachers_data = json.load(f)

# --- 各ユーザーの状態を保存するメモリ辞書 ---
user_state = {}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text

    # スタートメッセージ
    if user_message in ["スタート", "こんにちは", "相談", "はじめる"]:
        user_state[user_id] = {"step": "genre"}
        reply_genre_question(event)
        return

    # --- STEP1: ジャンル選択 ---
    if user_id in user_state and user_state[user_id].get("step") == "genre":
        selected_genre = user_message
        user_state[user_id]["genre"] = selected_genre
        user_state[user_id]["step"] = "detail"
        reply_detail_question(event, selected_genre)
        return

    # --- STEP2: 詳細質問に応じた教員紹介 ---
    if user_id in user_state and user_state[user_id].get("step") == "detail":
        selected_detail = user_message
        genre = user_state[user_id]["genre"]
        reply_teacher(event, genre, selected_detail)
        del user_state[user_id]
        return

    # その他の入力
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="「スタート」と入力して相談を始めてください。")
    )


# --- 各種関数 ---
def reply_genre_question(event):
    """ジャンル選択"""
    items = ["恋愛", "進路", "学習", "その他"]
    buttons = [QuickReplyButton(action=MessageAction(label=i, text=i)) for i in items]
    message = TextSendMessage(
        text="こんにちは！どんな悩みですか？",
        quick_reply=QuickReply(items=buttons)
    )
    line_bot_api.reply_message(event.reply_token, message)


def reply_detail_question(event, genre):
    """ジャンルに応じて次の質問を変える"""
    detail_options = {
        "恋愛": ["片思い", "失恋", "友人関係"],
        "進路": ["大学", "就職", "専門学校"],
        "学習": ["英語", "数学", "理科"],
        "その他": ["部活", "家庭", "人間関係"]
    }

    buttons = [QuickReplyButton(action=MessageAction(label=i, text=i)) for i in detail_options[genre]]
    message = TextSendMessage(
        text=f"{genre}の中で、どんな内容ですか？",
        quick_reply=QuickReply(items=buttons)
    )
    line_bot_api.reply_message(event.reply_token, message)


def reply_teacher(event, genre, detail):
    """ジャンル・詳細に応じた教員を返信"""
    for teacher in teachers_data:
        if genre in teacher["tags"] or detail in teacher["tags"]:
            text = f"おすすめの先生は {teacher['name']} 先生です。\n専門: {teacher['specialty']}"
            if "image" in teacher and teacher["image"]:
                line_bot_api.reply_message(
                    event.reply_token, [
                        TextSendMessage(text=text),
                        TextSendMessage(text=teacher["image"])
                    ]
                )
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))
            return

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="該当する先生が見つかりませんでした。"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
