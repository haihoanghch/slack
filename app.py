import os
from flask import Flask, request, jsonify
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

# Khởi tạo Flask trước
app = Flask(__name__)

# Lấy biến môi trường (Có giá trị mặc định để tránh crash)
token = os.environ.get("SLACK_BOT_TOKEN", "dummy-token")
secret = os.environ.get("SLACK_SIGNING_SECRET", "dummy-secret")

# Khởi tạo Bolt
bolt_app = App(token=token, signing_secret=secret, process_before_response=True)
handler = SlackRequestHandler(bolt_app)

@bolt_app.command("/crm")
@bolt_app.command("/ticket")
def handle_test(ack, say):
    ack()
    say("Hệ thống đã nhận lệnh! Server đang sống khỏe mạnh. ✅")

@app.route("/", methods=["POST"])
def slack_events():
    return handler.handle(request)

@app.route("/", methods=["GET"])
def health():
    return "OK - Server is Live", 200
