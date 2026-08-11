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
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Injected module reference (bot.py itself)
B = None


def bind(bot_module):
    global B
    B = bot_module


def _log(*a):
    if B:
        B.log("api:", *a)
    else:
        print("api:", *a)


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
        # use UTC epoch
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


def guest_public(g):
    if not g:
        return None
    lv = B.level_of(g["spent"])
    nx = B.next_level(g["spent"])
    stamp = int(g.get("stamp_count") or 0)
    return {
        "id": g["id"],
        "card": g["card"],
        "card_pretty": B.pretty_card(g["card"]),
        "name": g.get("name") or "",
        "last_name": g.get("last_name") or "",
        "phone": g.get("phone") or "",
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


class Handler(BaseHTTPRequestHandler):
    server_version = "IspovedAPI/2"

    def log_message(self, fmt, *args):
        _log(self.address_string(), fmt % args)

    def _cors(self):
        origin = B.API_CORS if B else "*"
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers",
                         "Content-Type, X-Telegram-InitData, Idempotency-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    def _auth(self, max_age=86400):
        init = (self.headers.get("X-Telegram-InitData")
                or self.headers.get("Authorization") or "")
        if init.lower().startswith("tma "):
            init = init[4:].strip()
        if not init:
            # query fallback for simple GETs in debug (not for staff mutations)
            q = urllib.parse.urlparse(self.path).query
            qs = urllib.parse.parse_qs(q)
            init = (qs.get("initData") or [""])[0]
        ok, user = validate_init_data(init, B.TOKEN, max_age=max_age)
        if not ok:
            return None, user
        return user, None

    def do_GET(self):
        if getattr(B, "MAINTENANCE", False):
            c, b = _json_bytes({"error": "maintenance"}, 503)
            return self._send(c, b)
        path = urllib.parse.urlparse(self.path).path

        if path in ("/api/health", "/health"):
            c, b = _json_bytes({
                "ok": True,
                "bot": getattr(B, "BOT_NAME", ""),
                "sheets": bool(B.SHEETS_URL),
                "webapp": bool(B.WEBAPP_URL),
            })
            return self._send(c, b)

        if path.startswith("/app/") or path in ("/app", "/"):
            return self._static(path)

        if path == "/api/me":
            user, err = self._auth()
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
            })
            return self._send(c, b)

        if path == "/api/qr":
            user, err = self._auth()
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            g = ensure_guest_from_user(user)
            try:
                png = B.png(str(g["card"]), scale=8, quiet=4)
                b64 = base64.b64encode(png).decode("ascii")
            except Exception as e:
                c, b = _json_bytes({"error": f"qr: {e}"}, 500)
                return self._send(c, b)
            c, b = _json_bytes({
                "ok": True,
                "card": g["card"],
                "card_pretty": B.pretty_card(g["card"]),
                "png_base64": b64,
            })
            return self._send(c, b)

        if path == "/api/history":
            user, err = self._auth()
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
            user, err = self._auth()
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            c, b = _json_bytes({"ok": True, "menu": B.MENU, "brand": B.BRAND})
            return self._send(c, b)

        c, b = _json_bytes({"error": "not found"}, 404)
        self._send(c, b)

    def do_POST(self):
        if getattr(B, "MAINTENANCE", False):
            c, b = _json_bytes({"error": "maintenance"}, 503)
            return self._send(c, b)
        path = urllib.parse.urlparse(self.path).path
        body = self._read_json()

        if path == "/api/register":
            user, err = self._auth()
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            g = ensure_guest_from_user(user)
            name = (body.get("name") or body.get("first_name") or g.get("name") or "").strip()[:64]
            last_name = (body.get("last_name") or "").strip()[:64]
            phone = (body.get("phone") or g.get("phone") or "").strip()[:32]
            gender = (body.get("gender") or "").strip()[:16]
            bday = (body.get("bday") or g.get("bday") or "").strip()[:16]
            kw = {}
            if name:
                kw["name"] = name
            # optional columns — update via raw SQL for new fields
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
                        c, b = _json_bytes({"error": str(e)}, 500)
                        return self._send(c, b)
            g2 = B.get(g["id"])
            c, b = _json_bytes({"ok": True, "guest": guest_public(g2)})
            return self._send(c, b)

        if path == "/api/staff/guest":
            user, err = self._auth(max_age=3600)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            if not B.is_staff(int(user["id"])):
                c, b = _json_bytes({"error": "forbidden"}, 403)
                return self._send(c, b)
            card = re.sub(r"\D", "", str(body.get("card") or body.get("q") or ""))
            # extract 6 digits if longer payload
            m = re.search(r"(\d{6})", card)
            if m:
                card = m.group(1)
            g = B.get_by_card(card) if card else None
            if not g and body.get("q"):
                found = B.find(str(body["q"]), 5)
                g = found[0] if found else None
            if not g:
                c, b = _json_bytes({"error": "Гость не найден"}, 404)
                return self._send(c, b)
            c, b = _json_bytes({"ok": True, "guest": guest_public(g)})
            return self._send(c, b)

        if path == "/api/staff/preview":
            user, err = self._auth(max_age=3600)
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
            user, err = self._auth(max_age=3600)
            if err:
                c, b = _json_bytes({"error": err}, 401)
                return self._send(c, b)
            if not B.is_staff(int(user["id"])):
                c, b = _json_bytes({"error": "forbidden"}, 403)
                return self._send(c, b)
            idk = (self.headers.get("Idempotency-Key")
                   or body.get("idempotency_key") or "")
            if not idk:
                c, b = _json_bytes({"error": "Idempotency-Key required",
                                    "code": "missing_idempotency_key"}, 400)
                return self._send(c, b)
            r = B.checkout(
                int(body.get("gid") or 0),
                int(body.get("total") or 0),
                int(body.get("use_pts") or 0),
                str(body.get("items") or ""),
                f"оф. {user['id']}",
                idempotency_key=idk,
                hookah=bool(body.get("hookah")),
                redeem_hookah=bool(body.get("redeem_hookah")),
            )
            if r.get("code") == "idempotency_mismatch":
                c, b = _json_bytes(r, 409)
                return self._send(c, b)
            if r.get("error"):
                c, b = _json_bytes(r, 400)
                return self._send(c, b)
            # notify guest only on first apply
            if not r.get("replay") and r.get("guest"):
                try:
                    B.notify_guest_visit(
                        r["guest"], r,
                        int(body.get("total") or 0),
                        int(r.get("paid") or 0))
                except Exception:
                    pass
            # serialize guest for JSON
            out = dict(r)
            if out.get("guest"):
                out["guest"] = guest_public(out["guest"])
            c, b = _json_bytes(out)
            return self._send(c, b)

        c, b = _json_bytes({"error": "not found"}, 404)
        self._send(c, b)

    def _static(self, path):
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
        dist = os.path.join(root, "dist")
        base = dist if os.path.isdir(dist) else root
        rel = path[len("/app"):] if path.startswith("/app") else path
        if not rel or rel == "/":
            rel = "/index.html"
        rel = rel.lstrip("/").replace("..", "")
        fpath = os.path.join(base, rel)
        if not os.path.isfile(fpath):
            # SPA fallback
            fpath = os.path.join(base, "index.html")
        if not os.path.isfile(fpath):
            c, b = _json_bytes({"error": "app not found — build app/"}, 404)
            return self._send(c, b)
        ctype = mimetypes.guess_type(fpath)[0] or "application/octet-stream"
        with open(fpath, "rb") as f:
            data = f.read()
        self._send(200, data, ctype)


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
