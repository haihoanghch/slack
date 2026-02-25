import os
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from supabase import create_client

# 1. Lấy biến môi trường và kiểm tra kỹ
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# 2. Khởi tạo Slack Bolt (Thêm điều kiện check để không crash)
if not SLACK_TOKEN or not SLACK_SECRET:
    print("❌ THIẾU BIẾN MÔI TRƯỜNG SLACK!")

bolt_app = App(
    token=SLACK_TOKEN,
    signing_secret=SLACK_SECRET,
    process_before_response=True
)

# 3. Khởi tạo Flask
app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)

# 4. Kết nối Supabase (Bọc trong Try-Except)
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase connected")
    except Exception as e:
        print(f"❌ Supabase Error: {e}")
else:
    print("❌ THIẾU BIẾN MÔI TRƯỜNG SUPABASE!")
