"""
Registration checker for the gym website.

How to use (in the VS Code terminal, inside the project folder):
    python check_registration.py

It creates ONE test member, then deletes it again. It never prints passwords.
"""

import importlib
import importlib.util
import os
import re
import sys
import traceback
from datetime import date

TEST_EMAIL = "registration-test@example.com"


def ok(msg):
    print("[OK]   " + msg)


def bad(msg):
    print("[FAIL] " + msg)


def info(msg):
    print("       " + msg)


def short_error(e):
    return "{}: {}".format(type(e).__name__, e)


print("=" * 60)
print("GYM WEBSITE - REGISTRATION CHECK")
print("=" * 60)
print("Python " + sys.version.split()[0])
print("Folder: " + os.getcwd())
print()

# ------------------------------------------------------------
# 1. Is this the right folder and the newest app.py?
# ------------------------------------------------------------
print("1) Project files")

if not os.path.exists("app.py"):
    bad("app.py not found here. Open the terminal in the project folder (the one with app.py).")
    sys.exit(1)

source = open("app.py", encoding="utf-8").read()

if "payment_records" in source and "def register_success" in source:
    ok("app.py is the newest version (payment recording, no online payment page)")
else:
    bad("app.py is an OLD version. Replace it with app.py from the latest zip.")

if "def pay_cursor" in source or 'route("/pay"' in source:
    bad("app.py still contains the old online payment page (/pay) - that is what breaks registration.")

for name in ("register.html", "register_success.html", "payments.html", "member_details.html"):
    path = os.path.join("templates", name)
    if os.path.exists(path):
        ok("templates/" + name)
    else:
        bad("templates/" + name + " is missing - copy the whole templates folder from the latest zip.")

for old in ("payment.html", "payment_error.html"):
    if os.path.exists(os.path.join("templates", old)):
        info("old file templates/" + old + " is still there. It is harmless, you can delete it.")

print()

# ------------------------------------------------------------
# 2. Python packages
# ------------------------------------------------------------
print("2) Python packages")

missing = False

for pkg in ("flask", "flask_session", "mysql.connector", "dotenv"):
    try:
        importlib.import_module(pkg)
        ok(pkg)
    except Exception as e:
        missing = True
        bad(pkg + " is not installed (" + short_error(e) + ")")

if missing:
    print()
    print("FIX: run these two lines, then run this checker again:")
    print("     source .venv/bin/activate")
    print("     pip install -r requirements.txt")
    print("(If there is no .venv folder: python3 -m venv .venv  first.)")
    sys.exit(1)

print()

# ------------------------------------------------------------
# 3. .env settings (names only - values are never shown)
# ------------------------------------------------------------
print("3) .env settings")

from dotenv import dotenv_values  # noqa: E402

if not os.path.exists(".env"):
    bad(".env file not found in this folder.")
    values = {}
else:
    values = dotenv_values(".env")

for key in ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE", "SECRET_KEY"):
    if values.get(key):
        ok(key + " is set")
    else:
        bad(key + " is missing or empty in .env")

for key in ("ADMIN_USERNAME", "ADMIN_PASSWORD"):
    if values.get(key):
        ok(key + " is set")
    else:
        info(key + " is not set (admin login will be disabled, registration is not affected)")

print()

# ------------------------------------------------------------
# 4. Database connection and members table
# ------------------------------------------------------------
print("4) Database")

import mysql.connector  # noqa: E402

conn = None

try:
    conn = mysql.connector.connect(
        host=values.get("MYSQL_HOST"),
        user=values.get("MYSQL_USER"),
        password=values.get("MYSQL_PASSWORD"),
        database=values.get("MYSQL_DATABASE"),
    )
    ok("connected to MySQL (database: {})".format(values.get("MYSQL_DATABASE")))
except Exception as e:
    bad("could not connect to MySQL: " + short_error(e))
    info("Is MySQL running? Are MYSQL_HOST / USER / PASSWORD / DATABASE in .env correct?")

if conn is not None:
    try:
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        tables = [r[0] for r in cur.fetchall()]
        info("tables: " + ", ".join(tables))

        if "members" not in tables:
            bad("the 'members' table does not exist in this database")
        else:
            cur.execute("DESCRIBE members")
            cols = cur.fetchall()
            info("members columns:")
            for c in cols:
                info("   {} ({}){}".format(
                    c[0], c[1], "  <- required, no default" if c[2] == "NO" and c[4] is None and "auto_increment" not in str(c[5]) else ""
                ))

            names = [c[0] for c in cols]
            needed = ["name", "email", "phone", "membership", "start_date", "expiry_date"]
            absent = [n for n in needed if n not in names]

            if absent:
                bad("members table has no column(s): " + ", ".join(absent))
            else:
                ok("members table has all the columns registration needs")

        cur.close()
    except Exception as e:
        bad("could not read the members table: " + short_error(e))

print()

# ------------------------------------------------------------
# 5. The real registration page, tested through the real app
# ------------------------------------------------------------
print("5) Registration page (real test, one test member is created then deleted)")

gym = None

try:
    spec = importlib.util.spec_from_file_location("gymapp", "app.py")
    gym = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gym)
    ok("app.py loads without errors")
except Exception as e:
    bad("app.py crashed while loading: " + short_error(e))
    print()
    traceback.print_exc(limit=-4)
    gym = None

if gym is not None:
    client = gym.app.test_client()

    try:
        r = client.get("/register")
        page = r.get_data(as_text=True)
        if r.status_code == 200 and "Gym Registration" in page:
            ok("GET /register shows the form (status 200)")
        else:
            bad("GET /register returned status {} (expected the form)".format(r.status_code))
    except Exception as e:
        bad("GET /register crashed: " + short_error(e))
        traceback.print_exc(limit=-4)

    try:
        today = date.today().strftime("%d-%m-%Y")
        r = client.post("/register", data={
            "name": "Registration Test",
            "email": TEST_EMAIL,
            "phone": "9999999999",
            "membership": "Monthly",
            "start_date": today,
        })

        if r.status_code == 302:
            where = r.headers.get("Location", "")
            ok("POST /register saved the member and redirected to " + where.split("?")[0])

            r2 = client.get(where)
            if r2.status_code == 200 and "Welcome" in r2.get_data(as_text=True):
                ok("the welcome page opens (status 200)")
            else:
                bad("the welcome page returned status {}".format(r2.status_code))
        else:
            page = r.get_data(as_text=True)
            m = re.search(r'class="pay-error">(.*?)</p>', page, re.S)
            bad("POST /register did not succeed (status {})".format(r.status_code))
            if m:
                info("message shown on the page: " + m.group(1).strip())
            else:
                info("first part of the page: " + re.sub(r"\s+", " ", page)[:300])

    except Exception as e:
        bad("POST /register crashed: " + short_error(e))
        traceback.print_exc(limit=-6)

    # clean up the test member
    try:
        gym.cursor.execute("DELETE FROM members WHERE email = %s", (TEST_EMAIL,))
        gym.db.commit()
        ok("test member removed again")
    except Exception as e:
        bad("could not remove the test member (delete 'Registration Test' from the dashboard): " + short_error(e))

print()
print("=" * 60)
print("Copy EVERYTHING printed above and send it to me.")
print("=" * 60)
