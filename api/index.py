import os
import logging
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from supabase import create_client

# Cấu hình log cơ bản ra màn hình console của Vercel
logging.basicConfig(level=logging.INFO)

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True
)

# Kiểm tra kết nối Supabase ngay khi khởi động
try:
    supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
    print("--- Kết nối Supabase thành công ---")
except Exception as e:
    print(f"--- Lỗi kết nối Supabase: {str(e)} ---")

def log_activity(user_id, command, content, status):
    try:
        print(f"Đang ghi log: {command} - {status}")
        supabase.table("logs").insert({
            "user_id": user_id,
            "command": command,
            "content": content,
            "status": status
        }).execute()
    except Exception as e:
        print(f"❌ Lỗi ghi log vào Supabase: {str(e)}")

@app.command("/crm")
@app.command("/ticket")
def handle_universal_commands(ack, body, say):
    ack()
    print(f"--- Nhận lệnh: {body.get('command')} từ {body.get('user_id')} ---")
    
    user_id = body["user_id"]
    command = body["command"]
    content = body.get("text", "")

    if not content:
        say("Vui lòng nhập nội dung sau câu lệnh!")
        return

    # Ghi log ban đầu
    log_activity(user_id, command, content, "pending")

    # Gửi tin nhắn phản hồi
    say(
        blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": f"📍 *Yêu cầu {command}:* {content}"}},
            {"type": "actions", "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "Xác nhận"}, "style": "primary", "action_id": "approve_btn", "value": f"{user_id}|{command}|{content}"}
            ]}
        ]
    )
