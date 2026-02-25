import os
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

# 1. Khởi tạo Slack Bolt (Dùng biến dummy để tránh crash nếu thiếu env)
bolt_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN", "xoxb-dummy"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET", "dummy"),
    process_before_response=True
)
handler = SlackRequestHandler(bolt_app)

# 2. Khởi tạo Flask và ĐẶT TÊN LÀ app
app = Flask(__name__)

@bolt_app.command("/crm")
@bolt_app.command("/ticket")
def handle_test(ack, say):
    ack()
    say("✅ Kết nối thành công! Serverless Function đang hoạt động.")

@app.route("/", defaults={"path": ""}, methods=["POST", "GET"])
@app.route("/<path:path>", methods=["POST", "GET"])
def index(path):
    if request.method == "GET":
        return "Server is Live!", 200
    return handler.handle(request)
