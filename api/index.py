import os
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from supabase import create_client
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

# --- Flask app ---
flask_app = Flask(__name__)

# --- Slack Bolt ---
bolt_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True
)
slack_handler = SlackRequestHandler(bolt_app)

# --- Supabase ---
supabase = None
try:
    supabase = create_client(
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_KEY")
    )
except Exception as e:
    print("Supabase error:", e)


# --- Slack commands ---
@bolt_app.command("/crm")
@bolt_app.command("/ticket")
def handle_universal_commands(ack, body, say):
    ack()
    user_id = body["user_id"]
    command = body["command"]
    content = body.get("text", "").strip()

    try:
        supabase.table("logs").insert({
            "user_id": user_id,
            "command": command,
            "content": content,
            "status": "pending"
        }).execute()
    except:
        pass

    say(
        blocks=[
            {"type": "section",
             "text": {"type": "mrkdwn",
                      "text": f"📍 *Yêu cầu {command}:* {content}"}},
            {"type": "actions",
             "elements": [
                 {"type": "button",
                  "text": {"type": "plain_text", "text": "Xác nhận"},
                  "style": "primary",
                  "action_id": "approve_btn",
                  "value": f"{user_id}|{command}|{content}"},
                 {"type": "button",
                  "text": {"type": "plain_text", "text": "Hủy"},
                  "style": "danger",
                  "action_id": "deny_btn",
                  "value": f"{user_id}|{command}|{content}"}
             ]}
        ]
    )


# --- Flask route ---
@flask_app.route("/", defaults={"path": ""}, methods=["GET", "POST"])
@flask_app.route("/<path:path>", methods=["GET", "POST"])
def all_routes(path):
    return slack_handler.handle(request)


# --- Vercel handler ---
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.run_flask()

    def do_POST(self):
        self.run_flask()

    def run_flask(self):
        parsed = urlparse(self.path)

        # build environ cho Flask
        environ = {
            "wsgi.input": self.rfile,
            "CONTENT_LENGTH": self.headers.get("Content-Length", 0),
            "CONTENT_TYPE": self.headers.get("Content-Type"),
            "REQUEST_METHOD": self.command,
            "PATH_INFO": parsed.path,
            "QUERY_STRING": parsed.query,
        }

        # response Flask
        response = flask_app.wsgi_app(environ, self.start_response)

        for data in response:
            self.wfile.write(data)

    def start_response(self, status, headers):
        code = int(status.split(" ")[0])
        self.send_response(code)
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
