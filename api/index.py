import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

# Cấu hình Slack App (Sử dụng Lazy Listeners cho Serverless nếu xử lý nặng)
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True # Quan trọng cho Serverless
)

# 1. Xử lý Slash Command: Gửi nút xác nhận
@app.command("/manage")
def handle_command(ack, body, say):
    ack() # Phải phản hồi trong < 3s
    
    user_id = body["user_id"]
    content = body["text"]
    
    # Giao diện nút bấm (Block Kit)
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"📋 *Yêu cầu mới:* {content}\nNgười tạo: <@{user_id}>"}
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Xác nhận ✅"},
                    "action_id": "approve_btn",
                    "value": f"{user_id}|{content}", # Lưu context
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Hủy ❌"},
                    "action_id": "deny_btn",
                    "style": "danger"
                }
            ]
        }
    ]
    say(blocks=blocks)

# 2. Xử lý logic khi nhấn nút
@app.action("approve_btn")
def handle_approve(ack, body, client, say):
    ack()
    
    current_user = body["user"]["id"]
    val = body["actions"][0]["value"].split("|")
    creator_id = val[0]
    task_content = val[1]

    # Kiểm tra quyền: Chỉ người tạo mới được bấm (hoặc logic @mention)
    if current_user != creator_id:
        client.chat_postEphemeral(
            channel=body["channel"]["id"],
            user=current_user,
            text="⚠️ Bạn không đủ quyền để thực hiện thao tác này."
        )
        return

    # THỰC HIỆN CÁC HÀM TƯƠNG ỨNG (Log, Email, Odoo)
    log_to_supabase(current_user, "APPROVED", task_content)
    # create_odoo_record(task_content)
    
    # Cập nhật tin nhắn để tránh bấm lại
    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text=f"✅ Đã xử lý bởi <@{current_user}>",
        blocks=[]
    )

def log_to_supabase(user, action, detail):
    # Sử dụng thư viện supabase-py để ghi log vào DB miễn phí
    print(f"Logging: {user} did {action} on {detail}")

# Adapter để chạy trên Vercel (Flask)
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

@flask_app.route("/api/index", methods=["POST"])
def slack_handler():
    return handler.handle(request)
