# -*- coding: utf-8 -*-
"""HTTP API for Telegram Mini App (stdlib only).

Started from bot.main() as a daemon thread. Serves:
  - /api/* JSON endpoints (initData auth)
  - /app/* static Mini App files from app/dist or app/
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import mimetypes
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Injected module reference (bot.py itself)
B = None

# ── security: rate limit (IP → timestamps) ────────────────────
_rl_lock = threading.Lock()
_rl_hits = defaultdict(deque)  # ip -> deque of epoch times
_RL_WINDOW = 60.0
_RL_MAX = 90          # general
_RL_MAX_MUTATE = 30   # POST admin/staff
_RL_MAX_AI = 12       # assistant chat

# per-user AI daily soft cap (tg_id -> (day, count))
_ai_day = {}
_AI_DAY_MAX = 80


def bind(bot_module):
    global B
    B = bot_module


def _log(*a):
    if B:
        B.log("api:", *a)
    else:
        print("api:", *a)


def _client_ip(handler):
    xff = handler.headers.get("X-Forwarded-For") or ""
    if xff:
        return xff.split(",")[0].strip()[:64]
    return handler.client_address[0] if handler.client_address else "?"


def _rate_ok(ip: str, mutate: bool = False, ai: bool = False) -> bool:
    now = time.time()
    if ai:
        limit = _RL_MAX_AI
        key = "ai:" + ip
    elif mutate:
        limit = _RL_MAX_MUTATE
        key = "m:" + ip
    else:
        limit = _RL_MAX
        key = "r:" + ip
    with _rl_lock:
        q = _rl_hits[key]
        while q and now - q[0] > _RL_WINDOW:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        if len(_rl_hits) > 5000:
            dead = [k for k, v in _rl_hits.items() if not v or now - v[-1] > _RL_WINDOW * 2]
            for k in dead[:2000]:
                _rl_hits.pop(k, None)
        return True


def _ai_day_ok(tg_id: int) -> bool:
    day = time.strftime("%Y-%m-%d", time.gmtime())
    with _rl_lock:
        d, n = _ai_day.get(tg_id, ("", 0))
        if d != day:
            d, n = day, 0
        if n >= _AI_DAY_MAX:
            return False
        _ai_day[tg_id] = (d, n + 1)
        return True


def _groq_key():
    return (getattr(B, "GROQ_API_KEY", None) or os.environ.get("GROQ_API_KEY") or "").strip()


def _assistant_system(guest, role: str) -> str:
    brand = getattr(B, "BRAND", {}) or {}
    loy = getattr(B, "LOYALTY", {}) or {}
    levels = loy.get("levels") or []
    lvl_txt = ", ".join(
        f'{x.get("name")} от {x.get("from")}₽ → {x.get("cashback")}%'
        for x in levels
    )
    g_bits = ""
    if guest:
        lv = guest.get("level") or {}
        g_bits = (
            f"\nТекущий гость: {guest.get('name') or 'Гость'}, "
            f"карта {guest.get('card_pretty') or guest.get('card')}, "
            f"бонусы {guest.get('bonus')}, уровень «{lv.get('name', 'Гость')}» "
            f"({lv.get('cashback', 5)}% кэшбэк), "
            f"штампы {guest.get('stamp_count') or 0}/7, "
            f"free-кальянов в запасе: {guest.get('free_hookah_pending') or 0}, "
            f"визитов: {guest.get('visits') or 0}."
        )
    role_note = ""
    if role in ("staff", "admin", "owner"):
        role_note = (
            f"\nСобеседник — сотрудник ({role}). Можно кратко подсказывать про "
            "проведение чека (карта + сумма), штампы и уровни. Не выдавай чужие "
            "персональные данные и не меняй роли сам — только объясняй, как это "
            "делается в панели Директор / в боте."
        )
    return (
        f"Ты — вежливый нейропомощник лаундж-бара «{brand.get('name', 'Исповедь')}» "
        f"({brand.get('kind', 'лаундж-бар')}), г. {brand.get('city', 'Пермь')}, "
        f"{brand.get('addr', '')}. Часы: {brand.get('hours', '')}. "
        f"Телефон: {brand.get('phone', '')}.\n"
        "Отвечай по-русски, коротко и по делу (2–6 предложений), тёплый премиум-тон. "
        "Помогай с программой лояльности, акциями, меню-концепцией, адресом, режимом, "
        "как показать QR официанту, как копятся бонусы.\n"
        f"Правила лояльности: welcome {loy.get('welcome', 300)} бонусов, "
        f"кэшбэк по уровням ({lvl_txt}), "
        f"бонусами можно оплатить до {loy.get('max_pay_percent', 30)}% чека, "
        f"день рождения +{loy.get('birthday', 1000)}, "
        "каждый 8-й кальян бесплатно (7 штампов → free).\n"
        "Не выдумывай цены, если не уверен — предложи открыть «Меню» в приложении. "
        "Не проси пароли, токены, чужие номера карт. Не обещай бронь, если не уверен — "
        "предложи написать директору через бота."
        f"{g_bits}{role_note}"
    )


def groq_chat(messages, max_tokens=500):
    """Call Groq OpenAI-compatible chat. Returns (ok, text_or_error)."""
    key = _groq_key()
    if not key:
        return False, "Нейропомощник не настроен (нет GROQ_API_KEY на сервере)"
    model = getattr(B, "GROQ_MODEL", None) or "llama-3.3-70b-versatile"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": max_tokens,
        "top_p": 0.9,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=data,
        method="POST",
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "User-Agent": "IspovedMiniApp/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        obj = json.loads(raw)
        choices = obj.get("choices") or []
        if not choices:
            return False, "пустой ответ модели"
        msg = (choices[0].get("message") or {}).get("content") or ""
        msg = msg.strip()
        if not msg:
            return False, "пустой ответ модели"
        return True, msg[:4000]
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            body = ""
        _log("groq HTTP", e.code, body)
        if e.code == 401:
            return False, "ключ Groq отклонён — проверьте GROQ_API_KEY"
        if e.code == 429:
            return False, "лимит Groq, подождите минуту"
        return False, "ошибка нейросети"
    except Exception as e:
        _log("groq err", repr(e))
        return False, "нейросеть недоступна"


# ── initData validation (Telegram WebApp) ─────────────────────
def validate_init_data(init_data: str, bot_token: str, max_age: int = 86400):
    """Return (ok, user_dict_or_error).

    Algorithm: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data or not bot_token:
        return False, "missing initData"
    try:
        parsed = urllib.parse.parse_qs(init_data, keep_blank_values=True)
        flat = {k: v[0] for k, v in parsed.items()}
    except Exception:
        return False, "bad initData encoding"
    recv_hash = flat.pop("hash", None)
    if not recv_hash:
        return False, "missing hash"
    # data_check_string: sorted key=value joined by \n
    pairs = sorted((k, v) for k, v in flat.items())
    data_check = "\n".join(f"{k}={v}" for k, v in pairs)
    secret = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calc = hmac.new(secret, data_check.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, recv_hash):
        return False, "bad hash"
    auth_date = int(flat.get("auth_date") or 0)
    if max_age and auth_date:
        if abs(int(time.time()) - auth_date) > max_age:
            return False, "stale auth_date"
    user_raw = flat.get("user")
    if not user_raw:
        return False, "missing user"
    try:
        user = json.loads(user_raw)
    except Exception:
        return False, "bad user json"
    if not user.get("id"):
        return False, "missing user.id"
    return True, user


def _json_bytes(obj, code=200):
    body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
    return code, body


def ensure_guest_from_user(user):
    """Soft-create guest on cold Mini App open (no prior /start). Welcome once."""
    tg_id = int(user["id"])
    name = " ".join(
        x for x in [user.get("first_name"), user.get("last_name")] if x
    )
    username = user.get("username") or ""
    g, _new = B.add_guest(tg_id, name, username)
    return g


def guest_public(g, staff_view=False):
    """Public guest payload. staff_view keeps phone; guest view masks partial PII if needed."""
    if not g:
        return None
    lv = B.level_of(g["spent"])
    nx = B.next_level(g["spent"])
    stamp = int(g.get("stamp_count") or 0)
    phone = g.get("phone") or ""
    return {
        "id": g["id"],
        "card": g["card"],
        "card_pretty": B.pretty_card(g["card"]),
        "name": g.get("name") or "",
        "last_name": g.get("last_name") or "",
        "phone": phone,
        "bday": g.get("bday") or "",
        "gender": g.get("gender") or "",
        "bonus": g["bonus"],
        "spent": g["spent"],
        "visits": g["visits"],
        "level": lv,
        "next_level": nx,
        "stamp_count": stamp,
        "stamps_needed": 7,
        "free_hookah_pending": int(g.get("free_hookah_pending") or 0),
        "profile_complete": int(g.get("profile_complete") or 0),
        "muted": int(g.get("muted") or 0),
        "brand": B.BRAND,
        "loyalty": {
            "cashback": lv["cashback"],
            "max_pay_percent": B.LOYALTY["max_pay_percent"],
            "welcome": B.LOYALTY["welcome"],
        },
    }


def role_public(r):
    """Safe role row for API (no internal notes leak beyond needed)."""
    if not r:
        return None
    return {
        "id": r["id"],
        "tg_id": int(r.get("tg_id") or 0),
        "username": r.get("username") or "",
        "role": r.get("role") or "",
        "role_name": B.ROLE_NAMES.get(r.get("role"), r.get("role")),
        "note": (r.get("note") or "")[:80],
        "added_by": (r.get("added_by") or "")[:40],
        "at": r.get("at") or "",
        "pending": not bool(r.get("tg_id")),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "IspovedAPI/3"

    # staff ops: 1h; admin mutations: 30m; guest reads: 24h
    MAX_AGE_GUEST = 86400
    MAX_AGE_STAFF = 3600
    MAX_AGE_ADMIN = 1800

    def log_message(self, fmt, *args):
        _log(self.address_string(), fmt % args)

    def _cors(self):
        origin = B.API_CORS if B else "*"
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers",
                         "Content-Type, X-Telegram-InitData, Idempotency-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")

    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if content_type.startswith("text/html"):
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self' https://telegram.org; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'self'",
            )
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 256_000:
            return {}
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    def _auth(self, max_age=86400, allow_query=False):
        """Validate Telegram WebApp initData. Query fallback only for debug GETs."""
        init = (self.headers.get("X-Telegram-InitData")
                or self.headers.get("Authorization") or "")
        if init.lower().startswith("tma "):
            init = init[4:].strip()
        if not init and allow_query:
            q = urllib.parse.urlparse(self.path).query
            qs = urllib.parse.parse_qs(q)
            init = (qs.get("initData") or [""])[0]
        ok, user = validate_init_data(init, B.TOKEN, max_age=max_age)
        if not ok:
            return None, user
        return user, None

    def _require_role(self, user, *allowed):
        """Check raw_role is in allowed. Returns (role, error_response_or_None)."""
        rid = int(user["id"])
        uname = user.get("username") or ""
        role = B.raw_role(rid, uname)
        if role not in allowed:
            return role, ("forbidden", 403)
        return role, None

    def do_GET(self):
        if getattr(B, "MAINTENANCE", False):
            c, b = _json_bytes({"error": "maintenance"}, 503)
            return self._send(c, b)

        ip = _client_ip(self)
        if not _rate_ok(ip, mutate=False):
            c, b = _json_bytes({"error": "too many requests"}, 429)
            return self._send(c, b)

        path = urllib.parse.urlparse(self.path).path

        if path in ("/api/health", "/health"):
            c, b = _json_bytes({
                "ok": True,
                "bot": getattr(B, "BOT_NAME", ""),
                "sheets": bool(B.SHEETS_URL),
                "webapp": bool(B.WEBAPP_URL),
                "assistant": bool(_groq_key()),
            })
            return self._send(c, b)

        # Mini App static
        if (path.startswith("/app/") or path in ("/app", "/")
                or path in ("/index.html", "/styles.css", "/app.js", "/config.js",
                            "/favicon.ico", "/bg-lounge.jpg")
                or path.endswith((".css", ".js", ".html", ".png", ".svg", ".ico",
                                  ".webp", ".jpg", ".jpeg", ".woff2"))):
            return self._static(path)

        if path == "/api/me":
            user, err = self._auth(max_age=self.MAX_AGE_GUEST)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            g = ensure_guest_from_user(user)
            role = B.raw_role(int(user["id"]), user.get("username") or "")
            c, b = _json_bytes({
                "ok": True,
                "tg_id": int(user["id"]),
                "role": role or "guest",
                "guest": guest_public(g),
                "assistant": bool(_groq_key()),
            })
            return self._send(c, b)

        if path == "/api/qr":
            user, err = self._auth(max_age=self.MAX_AGE_GUEST)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            g = ensure_guest_from_user(user)
            try:
                png = B.png(str(g["card"]), scale=8, quiet=4)
                b64 = base64.b64encode(png).decode("ascii")
            except Exception as e:
                _log("qr error", repr(e))
                c, b = _json_bytes({"error": "qr failed"}, 500)
                return self._send(c, b)
            c, b = _json_bytes({
                "ok": True,
                "card": g["card"],
                "card_pretty": B.pretty_card(g["card"]),
                "png_base64": b64,
            })
            return self._send(c, b)

        if path == "/api/history":
            user, err = self._auth(max_age=self.MAX_AGE_GUEST)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            g = ensure_guest_from_user(user)
            rows = B.history(g["id"], 30)
            out = []
            for v in rows:
                out.append({
                    "type": v.get("type"),
                    "total": v.get("total"),
                    "earned": v.get("earned"),
                    "paid_pts": v.get("paid_pts"),
                    "at": v.get("at"),
                    "why": v.get("extra_why") or "",
                })
            c, b = _json_bytes({"ok": True, "items": out})
            return self._send(c, b)

        if path == "/api/menu":
            user, err = self._auth(max_age=self.MAX_AGE_GUEST)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            c, b = _json_bytes({"ok": True, "menu": B.MENU, "brand": B.BRAND})
            return self._send(c, b)

        # ── Admin: stats ──
        if path == "/api/admin/stats":
            user, err = self._auth(max_age=self.MAX_AGE_ADMIN)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            role, ferr = self._require_role(user, "owner", "admin")
            if ferr:
                c, b = _json_bytes({"error": ferr[0]}, ferr[1])
                return self._send(c, b)
            s = B.stats()
            # strip heavy top list detail for wire size; keep levels
            c, b = _json_bytes({
                "ok": True,
                "role": role,
                "stats": {
                    "guests": s["guests"],
                    "active30": s["active30"],
                    "visits": s["visits"],
                    "revenue": s["revenue"],
                    "turnover": s.get("turnover", 0),
                    "avg": s["avg"],
                    "liability": s["liability"],
                    "given": s["given"],
                    "used": s["used"],
                    "today_visits": s["today_visits"],
                    "today_revenue": s["today_revenue"],
                    "levels": [{"name": n, "count": c} for n, c in s.get("levels", [])],
                    "top": [{"name": n, "qty": q} for n, q in (s.get("top") or [])[:8]],
                },
                "bot": {
                    "name": getattr(B, "BOT_NAME", ""),
                    "sheets": bool(B.SHEETS_URL),
                    "webapp": bool(B.WEBAPP_URL),
                    "maintenance": bool(getattr(B, "MAINTENANCE", False)),
                },
            })
            return self._send(c, b)

        # ── Admin: list roles ──
        if path == "/api/admin/roles":
            user, err = self._auth(max_age=self.MAX_AGE_ADMIN)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            role, ferr = self._require_role(user, "owner", "admin")
            if ferr:
                c, b = _json_bytes({"error": ferr[0]}, ferr[1])
                return self._send(c, b)
            rows = B.list_roles()
            # Director sees all but owner can manage owner roles
            c, b = _json_bytes({
                "ok": True,
                "role": role,
                "can_manage_owners": role == "owner",
                "can_grant": ["staff", "admin"] + (["owner"] if role == "owner" else []),
                "items": [role_public(r) for r in rows],
            })
            return self._send(c, b)

        c, b = _json_bytes({"error": "not found"}, 404)
        self._send(c, b)

    def do_POST(self):
        if getattr(B, "MAINTENANCE", False):
            c, b = _json_bytes({"error": "maintenance"}, 503)
            return self._send(c, b)

        ip = _client_ip(self)
        if not _rate_ok(ip, mutate=True):
            c, b = _json_bytes({"error": "too many requests"}, 429)
            return self._send(c, b)

        path = urllib.parse.urlparse(self.path).path
        body = self._read_json()

        # ── AI assistant (Groq, server-side key) ──
        if path == "/api/assistant":
            ip = _client_ip(self)
            if not _rate_ok(ip, ai=True):
                c, b = _json_bytes({"error": "слишком много запросов, подождите"}, 429)
                return self._send(c, b)
            user, err = self._auth(max_age=self.MAX_AGE_GUEST)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            if not _ai_day_ok(int(user["id"])):
                c, b = _json_bytes({"error": "дневной лимит помощника исчерпан"}, 429)
                return self._send(c, b)
            if not _groq_key():
                c, b = _json_bytes({
                    "error": "помощник не настроен — задайте GROQ_API_KEY на сервере",
                    "code": "no_groq_key",
                }, 503)
                return self._send(c, b)

            text = (body.get("message") or body.get("text") or "").strip()
            if not text:
                c, b = _json_bytes({"error": "пустой вопрос"}, 400)
                return self._send(c, b)
            if len(text) > 800:
                c, b = _json_bytes({"error": "слишком длинный вопрос (макс 800)"}, 400)
                return self._send(c, b)

            # optional short history from client (last turns only)
            history = body.get("history") or []
            if not isinstance(history, list):
                history = []
            clean_hist = []
            for h in history[-8:]:
                if not isinstance(h, dict):
                    continue
                role_h = h.get("role")
                content = (h.get("content") or "").strip()
                if role_h not in ("user", "assistant") or not content:
                    continue
                clean_hist.append({"role": role_h, "content": content[:800]})

            g = ensure_guest_from_user(user)
            gp = guest_public(g) or {}
            role = B.raw_role(int(user["id"]), user.get("username") or "") or "guest"
            messages = [{"role": "system", "content": _assistant_system(gp, role)}]
            messages.extend(clean_hist)
            messages.append({"role": "user", "content": text})

            ok, reply = groq_chat(messages)
            if not ok:
                c, b = _json_bytes({"error": reply}, 502)
                return self._send(c, b)
            c, b = _json_bytes({"ok": True, "reply": reply})
            return self._send(c, b)

        if path == "/api/register":
            user, err = self._auth(max_age=self.MAX_AGE_GUEST)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            g = ensure_guest_from_user(user)
            name = (body.get("name") or body.get("first_name") or g.get("name") or "").strip()[:64]
            last_name = (body.get("last_name") or "").strip()[:64]
            phone = (body.get("phone") or g.get("phone") or "").strip()[:32]
            gender = (body.get("gender") or "").strip()[:16]
            bday = (body.get("bday") or g.get("bday") or "").strip()[:16]
            # sanitize phone: digits + optional leading +
            if phone:
                phone = re.sub(r"[^\d+]", "", phone)[:32]
            with B._lock:
                sets, args = [], []
                if name:
                    sets.append("name=?"); args.append(name)
                if last_name:
                    sets.append("last_name=?"); args.append(last_name)
                if phone:
                    sets.append("phone=?"); args.append(phone)
                if gender:
                    sets.append("gender=?"); args.append(gender)
                if bday:
                    sets.append("bday=?"); args.append(bday)
                complete = 1 if (name and (phone or bday)) else int(g.get("profile_complete") or 0)
                sets.append("profile_complete=?"); args.append(complete)
                if body.get("sopd"):
                    sets.append("sopd_at=?"); args.append(B.now())
                if sets:
                    args.append(g["id"])
                    try:
                        B.conn().execute(
                            f"UPDATE guests SET {','.join(sets)} WHERE id=?", args)
                        B.conn().commit()
                    except Exception as e:
                        _log("register err", repr(e))
                        c, b = _json_bytes({"error": "save failed"}, 500)
                        return self._send(c, b)
            g2 = B.get(g["id"])
            c, b = _json_bytes({"ok": True, "guest": guest_public(g2)})
            return self._send(c, b)

        if path == "/api/staff/guest":
            user, err = self._auth(max_age=self.MAX_AGE_STAFF)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            if not B.is_staff(int(user["id"])):
                c, b = _json_bytes({"error": "forbidden"}, 403)
                return self._send(c, b)
            card = re.sub(r"\D", "", str(body.get("card") or body.get("q") or ""))
            m = re.search(r"(\d{6})", card)
            if m:
                card = m.group(1)
            g = B.get_by_card(card) if card else None
            if not g and body.get("q"):
                found = B.find(str(body["q"])[:64], 5)
                g = found[0] if found else None
            if not g:
                c, b = _json_bytes({"error": "Гость не найден"}, 404)
                return self._send(c, b)
            c, b = _json_bytes({"ok": True, "guest": guest_public(g, staff_view=True)})
            return self._send(c, b)

        if path == "/api/staff/preview":
            user, err = self._auth(max_age=self.MAX_AGE_STAFF)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            if not B.is_staff(int(user["id"])):
                c, b = _json_bytes({"error": "forbidden"}, 403)
                return self._send(c, b)
            p = B.preview(int(body.get("gid") or 0),
                          int(body.get("total") or 0),
                          int(body.get("use_pts") or 0))
            code = 200 if p.get("ok") else 400
            c, b = _json_bytes(p, code)
            return self._send(c, b)

        if path == "/api/staff/checkout":
            user, err = self._auth(max_age=self.MAX_AGE_STAFF)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            if not B.is_staff(int(user["id"])):
                c, b = _json_bytes({"error": "forbidden"}, 403)
                return self._send(c, b)
            idk = (self.headers.get("Idempotency-Key")
                   or body.get("idempotency_key") or "")
            if not idk or len(str(idk)) > 128:
                c, b = _json_bytes({"error": "Idempotency-Key required",
                                    "code": "missing_idempotency_key"}, 400)
                return self._send(c, b)
            total = int(body.get("total") or 0)
            use_pts = int(body.get("use_pts") or 0)
            if total < 0 or total > 5_000_000 or use_pts < 0 or use_pts > 5_000_000:
                c, b = _json_bytes({"error": "invalid amounts"}, 400)
                return self._send(c, b)
            r = B.checkout(
                int(body.get("gid") or 0),
                total,
                use_pts,
                str(body.get("items") or "")[:500],
                f"оф. {user['id']}",
                idempotency_key=str(idk)[:128],
                hookah=bool(body.get("hookah")),
                redeem_hookah=bool(body.get("redeem_hookah")),
            )
            if r.get("code") == "idempotency_mismatch":
                c, b = _json_bytes(r, 409)
                return self._send(c, b)
            if r.get("error"):
                c, b = _json_bytes({"error": r.get("error"), "code": r.get("code")}, 400)
                return self._send(c, b)
            if not r.get("replay") and r.get("guest"):
                try:
                    B.notify_guest_visit(
                        r["guest"], r,
                        total,
                        int(r.get("paid") or 0))
                except Exception:
                    pass
            out = dict(r)
            if out.get("guest"):
                out["guest"] = guest_public(out["guest"], staff_view=True)
            c, b = _json_bytes(out)
            return self._send(c, b)

        # ── Admin: grant role ──
        if path == "/api/admin/roles/grant":
            user, err = self._auth(max_age=self.MAX_AGE_ADMIN)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            my_role, ferr = self._require_role(user, "owner", "admin")
            if ferr:
                c, b = _json_bytes({"error": ferr[0]}, ferr[1])
                return self._send(c, b)

            want = (body.get("role") or "").strip().lower()
            if want not in ("owner", "admin", "staff"):
                c, b = _json_bytes({"error": "invalid role"}, 400)
                return self._send(c, b)
            # Director may only grant staff; owner can grant all
            if my_role == "admin" and want != "staff":
                c, b = _json_bytes({"error": "директор может выдавать только роль официанта"}, 403)
                return self._send(c, b)
            if my_role != "owner" and want == "owner":
                c, b = _json_bytes({"error": "только владелец выдаёт владельцев"}, 403)
                return self._send(c, b)

            username = B.norm_username(body.get("username") or "")
            tg_id = 0
            raw_id = body.get("tg_id")
            if raw_id is not None and str(raw_id).strip():
                try:
                    tg_id = int(str(raw_id).strip())
                except Exception:
                    c, b = _json_bytes({"error": "bad tg_id"}, 400)
                    return self._send(c, b)
            if not username and not tg_id:
                c, b = _json_bytes({"error": "укажите @username или Telegram ID"}, 400)
                return self._send(c, b)

            note = (body.get("note") or "из Mini App")[:80]
            by = f"{my_role} {user['id']}"
            try:
                row = B.grant(want, username=username, tg_id=tg_id, note=note, by=by)
            except Exception as e:
                _log("grant err", repr(e))
                c, b = _json_bytes({"error": "grant failed"}, 500)
                return self._send(c, b)
            if not row:
                c, b = _json_bytes({"error": "не удалось выдать роль"}, 400)
                return self._send(c, b)
            # notify if linked
            if row.get("tg_id"):
                try:
                    B._notify_role(int(row["tg_id"]), want)
                except Exception:
                    pass
            _log(f"ROLE GRANT {want} by {by} -> @{username or tg_id}")
            c, b = _json_bytes({"ok": True, "item": role_public(row)})
            return self._send(c, b)

        # ── Admin: revoke role ──
        if path == "/api/admin/roles/revoke":
            user, err = self._auth(max_age=self.MAX_AGE_ADMIN)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            my_role, ferr = self._require_role(user, "owner", "admin")
            if ferr:
                c, b = _json_bytes({"error": ferr[0]}, ferr[1])
                return self._send(c, b)

            try:
                rid = int(body.get("id") or 0)
            except Exception:
                rid = 0
            if not rid:
                c, b = _json_bytes({"error": "id required"}, 400)
                return self._send(c, b)

            rows = [r for r in B.list_roles() if r["id"] == rid]
            if not rows:
                c, b = _json_bytes({"error": "роль не найдена"}, 404)
                return self._send(c, b)
            target = rows[0]

            # Director cannot touch owner/admin roles
            if my_role == "admin" and target["role"] in ("owner", "admin"):
                c, b = _json_bytes({"error": "директор снимает только официантов"}, 403)
                return self._send(c, b)
            # cannot revoke self if last owner
            if target.get("tg_id") and int(target["tg_id"]) == int(user["id"]) and target["role"] == "owner":
                if B.count_owners() <= 1:
                    c, b = _json_bytes({"error": "нельзя снять единственного владельца"}, 400)
                    return self._send(c, b)

            by = f"{my_role} {user['id']}"
            ok, why = B.revoke(rid, by=by)
            if not ok:
                c, b = _json_bytes({"error": why}, 400)
                return self._send(c, b)
            _log(f"ROLE REVOKE id={rid} by {by}: {why}")
            c, b = _json_bytes({"ok": True, "revoked": why})
            return self._send(c, b)

        # ── Admin: link pending usernames ──
        if path == "/api/admin/roles/link":
            user, err = self._auth(max_age=self.MAX_AGE_ADMIN)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            my_role, ferr = self._require_role(user, "owner", "admin")
            if ferr:
                c, b = _json_bytes({"error": ferr[0]}, ferr[1])
                return self._send(c, b)
            linked = B.link_pending_roles()
            for r in linked:
                try:
                    B._notify_role(r["tg_id"], r["role"])
                except Exception:
                    pass
            c, b = _json_bytes({
                "ok": True,
                "linked": len(linked),
                "items": [role_public(r) for r in linked],
            })
            return self._send(c, b)

        # ── Admin: broadcast ──
        if path == "/api/admin/broadcast":
            user, err = self._auth(max_age=self.MAX_AGE_ADMIN)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            my_role, ferr = self._require_role(user, "owner", "admin")
            if ferr:
                c, b = _json_bytes({"error": ferr[0]}, ferr[1])
                return self._send(c, b)
            text = (body.get("text") or "").strip()
            if not text or len(text) < 2:
                c, b = _json_bytes({"error": "пустой текст"}, 400)
                return self._send(c, b)
            if len(text) > 3500:
                c, b = _json_bytes({"error": "слишком длинно (макс 3500)"}, 400)
                return self._send(c, b)
            # run async so HTTP doesn't hang
            admin_id = int(user["id"])
            _log(f"BROADCAST by {my_role} {admin_id}, len={len(text)}")

            def _run():
                try:
                    B.do_broadcast(admin_id, text)
                except Exception as e:
                    _log("broadcast err", repr(e))

            threading.Thread(target=_run, name="broadcast", daemon=True).start()
            c, b = _json_bytes({"ok": True, "queued": True, "message": "Рассылка запущена"})
            return self._send(c, b)

        # ── Admin: search guest ──
        if path == "/api/admin/guest":
            user, err = self._auth(max_age=self.MAX_AGE_ADMIN)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            my_role, ferr = self._require_role(user, "owner", "admin")
            if ferr:
                c, b = _json_bytes({"error": ferr[0]}, ferr[1])
                return self._send(c, b)
            q = str(body.get("q") or "").strip()[:64]
            if not q:
                c, b = _json_bytes({"error": "пустой запрос"}, 400)
                return self._send(c, b)
            found = B.find(q, 10)
            c, b = _json_bytes({
                "ok": True,
                "items": [guest_public(g, staff_view=True) for g in found],
            })
            return self._send(c, b)

        c, b = _json_bytes({"error": "not found"}, 404)
        self._send(c, b)

    def _static(self, path):
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
        dist = os.path.join(root, "dist")
        base = dist if os.path.isdir(dist) else root
        if path.startswith("/app"):
            rel = path[len("/app"):]
        else:
            rel = path
        if not rel or rel == "/":
            rel = "/index.html"
        rel = rel.lstrip("/").replace("..", "")
        fpath = os.path.join(base, rel)
        if not os.path.isfile(fpath):
            if rel.endswith((".html", "")) or "." not in rel:
                fpath = os.path.join(base, "index.html")
        if not os.path.isfile(fpath):
            c, b = _json_bytes({"error": "not found"}, 404)
            return self._send(c, b)
        ctype = mimetypes.guess_type(fpath)[0] or "application/octet-stream"
        if rel.endswith(".js"):
            ctype = "application/javascript; charset=utf-8"
        elif rel.endswith(".css"):
            ctype = "text/css; charset=utf-8"
        elif rel.endswith(".html"):
            ctype = "text/html; charset=utf-8"
        elif rel.endswith((".jpg", ".jpeg")):
            ctype = "image/jpeg"
        with open(fpath, "rb") as f:
            data = f.read()
        # cache static assets briefly (bg image)
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if rel.endswith((".jpg", ".jpeg", ".png", ".webp", ".svg", ".woff2")):
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            self.send_header("Cache-Control", "no-store")
        if ctype.startswith("text/html"):
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self' https://telegram.org; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'self'",
            )
        self.end_headers()
        self.wfile.write(data)


def start_background(host, port):
    if not port:
        _log("HTTP API disabled (API_PORT=0)")
        return None

    def run():
        try:
            httpd = ThreadingHTTPServer((host, port), Handler)
            _log(f"HTTP listening on {host}:{port}")
            httpd.serve_forever()
        except Exception as e:
            _log("HTTP failed:", repr(e))

    t = threading.Thread(target=run, name="ispoved-http", daemon=True)
    t.start()
    return t
