import os
import logging
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from supabase import create_client

# 1. Khởi tạo Flask TRƯỚC và đặt tên là 'app'
app = Flask(__name__)

# 2. Khởi tạo Slack Bolt App 
bolt_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True
)
handler = SlackRequestHandler(bolt_app)

# 3. Kết nối Supabase
try:
    supabase = create_client(
        os.environ.get("SUPABASE_URL"), 
        os.environ.get("SUPABASE_KEY")
    )
except Exception as e:
    print(f"Supabase Init Error: {e}")

# --- LOGIC SLACK (Giữ nguyên) ---

@bolt_app.command("/crm")
@bolt_app.command("/ticket")
def handle_universal_commands(ack, body, say):
    ack()
    user_id = body["user_id"]
    command = body["command"]
    content = body.get("text", "").strip()
    
    # Ghi log (pending)
    try:
        supabase.table("logs").insert({"user_id": user_id, "command": command, "content": content, "status": "pending"}).execute()
    except: pass

    say(
        blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": f"📍 *Yêu cầu {command}:* {content}"}},
            {"type": "actions", "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "Xác nhận ✅"}, "style": "primary", "action_id": "approve_btn", "value": f"{user_id}|{command}|{content}"},
                {"type": "button", "text": {"type": "plain_text", "text": "Hủy ❌"}, "style": "danger", "action_id": "deny_btn", "value": f"{user_id}|{command}|{content}"}
            ]}
        ]
    )

@bolt_app.action("approve_btn")
def handle_approve(ack, body, client):
    ack()
    val = body["actions"][0]["value"].split("|")
    if body["user"]["id"] != val[0]:
        client.chat_postEphemeral(channel=body["channel"]["id"], user=body["user"]["id"], text="❌ Không có quyền!")
        return
    
    # Cập nhật log & UI
    try:
        supabase.table("logs").update({"status": "approved"}).match({"user_id": val[0], "content": val[2]}).execute()
    except: pass

    client.chat_update(channel=body["channel"]["id"], ts=body["message"]["ts"], text=f"✅ Đã duyệt {val[1]}: {val[2]}", blocks=[])

@bolt_app.action("deny_btn")
def handle_deny(ack, body, client):
    ack()
    val = body["actions"][0]["value"].split("|")
    client.chat_update(channel=body["channel"]["id"], ts=body["message"]["ts"], text=f"🔴 Đã hủy: {val[2]}", blocks=[])

# 4. ROUTE quan trọng nhất cho Vercel
@app.route("/", defaults={"path": ""}, methods=["POST", "GET"])
@app.route("/<path:path>", methods=["POST", "GET"])
def slack_handler(path):
    return handler.handle(request)
