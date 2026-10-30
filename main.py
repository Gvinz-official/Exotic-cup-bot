import hashlib, hmac, html, json, os, threading, time, urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl

import gspread
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()
BOT_TOKEN = os.environ["BOT_TOKEN"]
SHEET_ID = os.environ["SHEET_ID"]
CREDS = os.getenv("GOOGLE_CREDS_FILE", "service_account.json")
JSON_PATH = Path("teams.json")
MAX_TEAMS = int(os.getenv("MAX_TEAMS", "32"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

app = FastAPI()
lock = threading.Lock()
sheet = gspread.service_account(filename=CREDS).open_by_key(SHEET_ID).sheet1
HEADERS = ["Дата", "Команда", "Капитан", "Контакт", "Состав", "Telegram ID", "Username"]
if not sheet.row_values(1):
    sheet.append_row(HEADERS)


def notify_admin(text: str):
    if not ADMIN_CHAT_ID:
        return
    try:
        data = json.dumps({"chat_id": ADMIN_CHAT_ID, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data,
            {"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


class Registration(BaseModel):
    init_data: str
    team_name: str = Field(min_length=2, max_length=40)
    captain: str = Field(min_length=2, max_length=60)
    contact: str = Field(min_length=3, max_length=60)
    players: str = Field(max_length=500)


def verify_init_data(init_data: str) -> dict:
    """Проверка подписи Telegram: данные точно пришли из Mini App."""
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received = parsed.pop("hash", None)
    check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not received or not hmac.compare_digest(calc, received):
        raise HTTPException(403, "Неверная подпись Telegram")
    if time.time() - int(parsed.get("auth_date", 0)) > 86400:
        raise HTTPException(403, "Сессия устарела, откройте приложение заново")
    return json.loads(parsed["user"])


def load_teams() -> list:
    if JSON_PATH.exists():
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return []


@app.post("/register")
def register(data: Registration):  # обычная def: FastAPI запустит в потоке
    user = verify_init_data(data.init_data)
    with lock:
        teams = load_teams()
        if len(teams) >= MAX_TEAMS:
            raise HTTPException(409, "Все места заняты")
        if any(t["team_name"].casefold() == data.team_name.casefold() for t in teams):
            raise HTTPException(409, "Команда с таким названием уже есть")
        if any(t["tg_id"] == user["id"] for t in teams):
            raise HTTPException(409, "Вы уже зарегистрировали команду")

        team = {
            "created": datetime.now().isoformat(timespec="seconds"),
            "team_name": data.team_name.strip(),
            "captain": data.captain.strip(),
            "contact": data.contact.strip(),
            "players": data.players.strip(),
            "tg_id": user["id"],
            "tg_username": user.get("username", ""),
        }
        sheet.append_row(list(team.values()))  # сначала таблица
        teams.append(team)
        JSON_PATH.write_text(json.dumps(teams, ensure_ascii=False, indent=2), encoding="utf-8")
    notify_admin(f"Новая команда #{len(teams)}: {team['team_name']} (капитан {team['captain']}, {team['contact']})")
    return {"ok": True, "place": len(teams)}


def check_admin(token: str):
    if not ADMIN_TOKEN or not hmac.compare_digest(token, ADMIN_TOKEN):
        raise HTTPException(403, "Нет доступа")


@app.get("/admin", response_class=HTMLResponse)
def admin(token: str = ""):
    check_admin(token)
    rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in t.values()) + "</tr>"
        for t in load_teams())
    head = "".join(f"<th>{h}</th>" for h in HEADERS)
    return f"""<meta charset=utf-8><meta name=viewport content="width=device-width">
<style>body{{font-family:sans-serif;padding:12px}}table{{border-collapse:collapse}}
td,th{{border:1px solid #ccc;padding:6px;font-size:14px}}</style>
<h3>Команды: {len(load_teams())} / {MAX_TEAMS}</h3>
<div style="overflow-x:auto"><table><tr>{head}</tr>{rows}</table></div>
<p><a href="/teams.json?token={html.escape(token)}">teams.json</a></p>"""


@app.get("/teams.json")
def teams_json(token: str = ""):
    check_admin(token)
    return load_teams()


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
