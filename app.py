from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction, FlexSendMessage
import os, json, random

app = Flask(__name__)

# 環境変数
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 教員データ
with open("teachers.json", "r", encoding="utf-8") as f:
    teachers_data = json.load(f)

# ユーザー状態管理
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
    text = event.message.text.strip()

    # スタート
    if text in ["スタート", "相談", "はじめる", "こんにちは"]:
        user_state[user_id] = {"step": "genre"}
        show_genre(event.reply_token)
        return

    # STEP1: ジャンル選択
    if user_id in user_state and user_state[user_id].get("step") == "genre":
        user_state[user_id]["genre"] = text
        user_state[user_id]["step"] = "detail"
        show_detail(event.reply_token, text)
        return

    # STEP2: 詳細選択 → 教員紹介
    if user_id in user_state and user_state[user_id].get("step") == "detail":
        genre = user_state[user_id]["genre"]
        detail = text
        show_teacher(event.reply_token, genre, detail)
        del user_state[user_id]
        return

    # それ以外
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="「スタート」と入力して相談を始めてください。")
    )


# --- ジャンル選択 ---
def show_genre(reply_token):
    items = ["恋愛", "進路", "学習", "その他"]
    buttons = [QuickReplyButton(action=MessageAction(label=i, text=i)) for i in items]
    message = TextSendMessage(
        text="こんにちは！どんな悩みですか？",
        quick_reply=QuickReply(items=buttons)
    )
    line_bot_api.reply_message(reply_token, message)


# --- 詳細選択 ---
def show_detail(reply_token, genre):
    options = {
        "恋愛": ["片思い", "失恋", "友人関係"],
        "進路": ["大学", "就職", "専門学校"],
        "学習": ["英語", "数学", "理科"],
        "その他": ["生活", "家庭", "人間関係"]
    }
    buttons = [QuickReplyButton(action=MessageAction(label=o, text=o)) for o in options.get(genre, ["その他"])]
    message = TextSendMessage(
        text=f"{genre}の中で、どの内容ですか？",
        quick_reply=QuickReply(items=buttons)
    )
    line_bot_api.reply_message(reply_token, message)


# --- 教員紹介（画像あり/なし対応） ---
def show_teacher(reply_token, genre, detail):
    matches = [
        t for t in teachers_data
        if genre in t.get("tags", []) or detail in t.get("tags", [])
    ]

    if not matches:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="条件に合う先生が見つかりませんでした。"))
        return

    teacher = random.choice(matches)

    if teacher.get("photo_url"):  # 画像あり
        message = FlexSendMessage(
            alt_text="おすすめの先生",
            contents={
                "type": "bubble",
                "hero": {
                    "type": "image",
                    "url": teacher["photo_url"],
                    "size": "full",
                    "aspectRatio": "1:1",
                    "aspectMode": "cover"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": teacher["name"], "weight": "bold", "size": "xl"},
                        {"type": "text", "text": teacher.get("comment", ""), "wrap": True}
                    ]
                }
            }
        )
        line_bot_api.reply_message(reply_token, message)
    else:  # 画像なし
        text = f"おすすめの先生は {teacher['name']} 先生です。\n{teacher.get('comment','')}"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=text))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
