from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage,
    ButtonsTemplate, PostbackAction, FlexSendMessage
)
import json, random, os

app = Flask(__name__)

# 環境変数から取得
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ユーザー状態管理
user_state = {}

# 教員データ読み込み
with open("teachers.json", "r", encoding="utf-8") as f:
    teachers = json.load(f)


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

    # 初回
    if user_id not in user_state:
        user_state[user_id] = {"step": 1}
        show_main_menu(event.reply_token)
        return

    state = user_state[user_id]

    # ステップ1：悩みの種類選択
    if state["step"] == 1:
        state["main_tag"] = text
        state["step"] = 2
        show_sub_question(event.reply_token, text)
        return

    # ステップ2：詳細選択 → 教員紹介
    elif state["step"] == 2:
        main_tag = state["main_tag"]
        sub_tag = text
        teacher = get_teacher(main_tag, sub_tag)

        if teacher:
            send_teacher_card(event.reply_token, teacher)
        else:
            line_bot_api.reply_message(event.reply_token,
                TextSendMessage(text="条件に合う先生が見つかりませんでした。"))

        del user_state[user_id]  # 状態リセット
        return


# メインカテゴリ表示
def show_main_menu(reply_token):
    buttons_template = ButtonsTemplate(
        title="相談の種類を選んでください",
        text="あなたの悩みのジャンルは？",
        actions=[
            PostbackAction(label="恋愛", data="恋愛", display_text="恋愛"),
            PostbackAction(label="進路", data="進路", display_text="進路"),
            PostbackAction(label="学習", data="学習", display_text="学習"),
            PostbackAction(label="その他", data="その他", display_text="その他")
        ]
    )
    message = TemplateSendMessage(alt_text="相談の種類", template=buttons_template)
    line_bot_api.reply_message(reply_token, message)


# サブ質問（カテゴリ別）
def show_sub_question(reply_token, category):
    questions = {
        "恋愛": ["片思い", "失恋", "友達関係"],
        "進路": ["大学進学", "専門学校", "就職"],
        "学習": ["英語", "数学", "国語"],
        "その他": ["生活", "人間関係", "健康"]
    }
    options = questions.get(category, ["その他"])

    actions = [PostbackAction(label=o, data=o, display_text=o) for o in options]
    buttons_template = ButtonsTemplate(
        title=f"{category}についてもう少し教えてください",
        text="どの内容に近いですか？",
        actions=actions
    )
    message = TemplateSendMessage(alt_text=f"{category}の詳細", template=buttons_template)
    line_bot_api.reply_message(reply_token, message)


# 教員データ検索
def get_teacher(main_tag, sub_tag):
    matches = [
        t for t in teachers if main_tag in t["tags"] and sub_tag in t["sub_tags"]
    ]
    return random.choice(matches) if matches else None


# 教員カード表示（Flex）
def send_teacher_card(reply_token, t):
    message = FlexSendMessage(
        alt_text="おすすめの先生",
        contents={
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": t["photo_url"],
                "size": "full",
                "aspectRatio": "1:1",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": t["name"], "weight": "bold", "size": "xl"},
                    {"type": "text", "text": t["comment"], "wrap": True}
                ]
            }
        }
    )
    line_bot_api.reply_message(reply_token, message)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
