import os
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from supabase import create_client

# 1. Khởi tạo Slack Bolt
bolt_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True
)

# 2. Khởi tạo Flask - ĐẶT TÊN LÀ 'app' ĐỂ VERCEL NHẬN DIỆN
app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)

# 3. Kết nối Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key) if url and key else None

# --- LOGIC XỬ LÝ LỆNH TẬP TRUNG ---
@bolt_app.command("/crm")
@bolt_app.command("/ticket")
def handle_commands(ack, body, say):
    ack()
    user_id = body["user_id"]
    command = body["command"]
    content = body.get("text", "").strip()

    if not content:
        say(f"Vui lòng nhập nội dung cho {command}")
        return

    # Ghi log ban đầu (Nếu có Supabase)
    if supabase:
        try:
            supabase.table("logs").insert({
                "user_id": user_id, 
                "command": command, 
                "content": content, 
                "status": "pending"
            }).execute()
        except Exception as e:
            print(f"Log Error: {e}")

    # Gửi nút bấm
    say(
        blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": f"🚀 *Yêu cầu {command}:* {content}"}},
            {"type": "actions", "elements": [
                {
                    "type": "button", 
                    "text": {"type": "plain_text", "text": "Xác nhận"}, 
                    "style": "primary", 
                    "action_id": "approve_click", 
                    "value": f"{user_id}|{command}|{content}"
                },
                {
                    "type": "button", 
                    "text": {"type": "plain_text", "text": "Hủy"}, 
                    "style": "danger", 
                    "action_id": "deny_click",
                    "value": f"{user_id}|{command}|{content}"
                }
            ]}
        ]
    )

# --- XỬ LÝ NÚT BẤM ---
@bolt_app.action("approve_click")
def handle_approve(ack, body, client):
    ack()
    val = body["actions"][0]["value"].split("|")
    creator_id, command, content = val[0], val[1], val[2]
    
    if body["user"]["id"] != creator_id:
        client.chat_postEphemeral(channel=body["channel"]["id"], user=body["user"]["id"], text="❌ Bạn không có quyền!")
        return

    # Cập nhật log approved
    if supabase:
        supabase.table("logs").update({"status": "approved"}).match({"user_id": creator_id, "content": content}).execute()

    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text=f"✅ Đã thực hiện {command}: {content}",
        blocks=[]
    )

@bolt_app.action("deny_click")
def handle_deny(ack, body, client):
    ack()
    val = body["actions"][0]["value"].split("|")
    if supabase:
        supabase.table("logs").update({"status": "denied"}).match({"user_id": val[0], "content": val[2]}).execute()
        
    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text=f"🔴 Đã hủy yêu cầu: {val[2]}",
        blocks=[]
    )

# --- ROUTE CHO VERCEL ---
@app.route("/", methods=["POST"])
def slack_events():
    return handler.handle(request)

@app.route("/", methods=["GET"])
def health_check():
    return "Server is running!", 200
