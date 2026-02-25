import os
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from supabase import create_client

# Khởi tạo Slack và Supabase
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True
)
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# Hàm ghi log
def log_activity(user_id, command, content, status):
    supabase.table("logs").insert({
        "user_id": user_id,
        "command": command,
        "content": content,
        "status": status
    }).execute()

# --- XỬ LÝ COMMANDS (/crm và /ticket) ---
@app.command("/crm")
@app.command("/ticket")
def handle_universal_commands(ack, body, say):
    ack()
    user_id = body["user_id"]
    command = body["command"]
    content = body["text"]

    if not content:
        say(f"Vui lòng nhập nội dung cho {command}")
        return

    log_activity(user_id, command, content, "pending")

    say(
        blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": f"📍 *Yêu cầu {command}:* {content}\nNgười tạo: <@{user_id}>"}},
            {"type": "actions", "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "Xác nhận"}, "style": "primary", "action_id": "approve_btn", "value": f"{user_id}|{command}|{content}"},
                {"type": "button", "text": {"type": "plain_text", "text": "Hủy"}, "style": "danger", "action_id": "deny_btn", "value": f"{user_id}|{command}|{content}"}
            ]}
        ]
    )

# --- XỬ LÝ NÚT BẤM ---
@app.action("approve_btn")
def handle_approve(ack, body, client):
    ack()
    val = body["actions"][0]["value"].split("|")
    creator_id, command, content = val[0], val[1], val[2]
    
    if body["user"]["id"] != creator_id:
        client.chat_postEphemeral(channel=body["channel"]["id"], user=body["user"]["id"], text="❌ Bạn không có quyền!")
        return

    # Logic xử lý riêng cho từng loại lệnh
    msg = "Đã xử lý"
    if command == "/crm":
        msg = "🚀 Đã tạo Lead CRM" # Thêm hàm gọi Odoo tại đây
    elif command == "/ticket":
        msg = "🎫 Đã tạo Ticket hỗ trợ"

    log_activity(creator_id, command, content, "approved")
    client.chat_update(channel=body["channel"]["id"], ts=body["message"]["ts"], text=f"✅ {msg}: {content}", blocks=[])

@app.action("deny_btn")
def handle_deny(ack, body, client):
    ack()
    val = body["actions"][0]["value"].split("|")
    log_activity(val[0], val[1], val[2], "denied")
    client.chat_update(channel=body["channel"]["id"], ts=body["message"]["ts"], text=f"🔴 Đã hủy yêu cầu: {val[2]}", blocks=[])

# Flask Adapter
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)
@flask_app.route("/", defaults={"path": ""}, methods=["POST"])
@flask_app.route("/<path:path>", methods=["POST"])
def slack_handler(path):
    return handler.handle(request)
