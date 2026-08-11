# -*- coding: utf-8 -*-
"""Golden tests for checkout + idempotency (stdlib unittest)."""
import os
import sys
import tempfile
import unittest

# Isolate DB before importing bot
_fd, _DB = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["BOT_TOKEN"] = "0000000000:TEST_TOKEN_FOR_UNITTESTS_ONLY________"
os.environ["DB_PATH"] = _DB
os.environ["SHEETS_URL"] = ""
os.environ["API_PORT"] = "0"
os.environ["OWNERS"] = ""

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bot  # noqa: E402


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        bot.close()
        if os.path.exists(_DB):
            os.remove(_DB)
        for s in ("-wal", "-shm"):
            p = _DB + s
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        bot._conn = None
        bot.conn()
        self.g, _ = bot.add_guest(1001, "Тест", "testuser")

    def tearDown(self):
        bot.close()

    def test_basic_earn(self):
        r = bot.checkout(self.g["id"], 1000, 0, "", "test",
                         idempotency_key="k1")
        self.assertTrue(r.get("ok"))
        self.assertEqual(r["paid"], 0)
        # 5% of 1000
        self.assertEqual(r["earned"], 50)
        g2 = bot.get(self.g["id"])
        self.assertEqual(g2["bonus"], self.g["bonus"] + 50)
        self.assertEqual(g2["spent"], 1000)
        self.assertEqual(g2["visits"], 1)

    def test_pay_cap_30_percent(self):
        # force high bonus
        bot.conn().execute("UPDATE guests SET bonus=5000 WHERE id=?", (self.g["id"],))
        bot.conn().commit()
        r = bot.checkout(self.g["id"], 1000, 99999, "", "t",
                         idempotency_key="k2")
        self.assertTrue(r.get("ok"))
        self.assertEqual(r["paid"], 300)  # 30% of 1000
        self.assertEqual(r["earned"], 35)  # 5% of 700

    def test_idempotent_double(self):
        r1 = bot.checkout(self.g["id"], 500, 0, "", "t",
                          idempotency_key="same")
        r2 = bot.checkout(self.g["id"], 500, 0, "", "t",
                          idempotency_key="same")
        self.assertTrue(r1.get("ok"))
        self.assertTrue(r2.get("ok"))
        self.assertTrue(r2.get("replay"))
        visits = bot.conn().execute(
            "SELECT COUNT(*) c FROM visits WHERE guest_id=? AND type='visit'",
            (self.g["id"],)).fetchone()["c"]
        self.assertEqual(visits, 1)

    def test_idempotency_mismatch(self):
        bot.checkout(self.g["id"], 500, 0, "", "t", idempotency_key="m1")
        r = bot.checkout(self.g["id"], 900, 0, "", "t", idempotency_key="m1")
        self.assertEqual(r.get("code"), "idempotency_mismatch")

    def test_atomicity_key_with_visit(self):
        bot.checkout(self.g["id"], 200, 0, "", "t", idempotency_key="atom")
        v = bot.conn().execute(
            "SELECT COUNT(*) c FROM visits WHERE guest_id=? AND type='visit'",
            (self.g["id"],)).fetchone()["c"]
        k = bot.conn().execute(
            "SELECT COUNT(*) c FROM idempotency_keys WHERE key=?",
            ("atom",)).fetchone()["c"]
        self.assertEqual(v, 1)
        self.assertEqual(k, 1)

    def test_canonical_hash_stable(self):
        h1 = bot._canonical_checkout_hash(1, 100, 0, "", "a")
        h2 = bot._canonical_checkout_hash(1, 100, 0, "", "a")
        h3 = bot._canonical_checkout_hash(1, 100, 10, "", "a")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)

    def test_blocked(self):
        bot.conn().execute("UPDATE guests SET blocked=1 WHERE id=?", (self.g["id"],))
        bot.conn().commit()
        r = bot.checkout(self.g["id"], 100, 0, "", "t", idempotency_key="b")
        self.assertIn("error", r)


if __name__ == "__main__":
    unittest.main()
