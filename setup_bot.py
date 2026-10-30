"""Один раз: ставит в боте кнопку «Регистрация» с вашим Mini App."""
import json, os, urllib.request
from dotenv import load_dotenv

load_dotenv()
token, url = os.environ["BOT_TOKEN"], os.environ["WEBAPP_URL"]
body = {"menu_button": {"type": "web_app", "text": "Регистрация", "web_app": {"url": url}}}
req = urllib.request.Request(f"https://api.telegram.org/bot{token}/setChatMenuButton",
                             json.dumps(body).encode(), {"Content-Type": "application/json"})
print(urllib.request.urlopen(req).read().decode())
