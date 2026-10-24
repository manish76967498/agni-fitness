from flask import Flask, render_template, request, redirect, url_for, session, flash  # pyright: ignore[reportMissingImports]
import mysql.connector  # pyright: ignore[reportMissingImports]
from flask_session import Session  # pyright: ignore[reportMissingImports]
from datetime import date, datetime, timedelta
import calendar
import os
import re
import secrets
try:
    from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False
load_dotenv()

app = Flask(__name__)


# =========================================================
# NO CACHE
# =========================================================

@app.after_request
def add_no_cache(response):

    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )

    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


# =========================================================
# FLASK SESSION
# =========================================================

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SESSION_TYPE"] = "filesystem"

Session(app)


# =========================================================
# MYSQL DATABASE CONNECTION
# =========================================================

db = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE")
)
cursor = db.cursor()


# =========================================================
# FUNCTION: ADD MONTHS
# =========================================================

def add_months(original_date, months):

    month = original_date.month - 1 + months

    year = original_date.year + month // 12

    month = month % 12 + 1

    day = min(
        original_date.day,
        calendar.monthrange(year, month)[1]
    )

    return date(year, month, day)


# =========================================================
# FUNCTION: PARSE DATE
# =========================================================

def parse_date(date_string):

    date_string = date_string.strip()

    # HTML calendar picker format
    try:
        return datetime.strptime(
            date_string,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        pass

    # Older format
    try:
        return datetime.strptime(
            date_string,
            "%d-%m-%Y"
        ).date()

    except ValueError:

        raise ValueError("Invalid date")


# =========================================================
# HOME PAGE
# =========================================================

# =========================================================
# MEMBERSHIP PLANS (single source of truth for the website)
# Edit prices / features here. Prices are placeholders.
# =========================================================

PLANS = [
    {"name": "Monthly", "label": "Monthly", "price": 1500, "period": "1 month",
     "perks": ["Full gym access", "Locker facility", "Cardio & weights zone"]},
    {"name": "3 Months", "label": "3 Months", "price": 4000, "period": "3 months",
     "perks": ["Full gym access", "Locker facility", "1 free fitness assessment"]},
    {"name": "6 Months", "label": "6 Months", "price": 7000, "period": "6 months",
     "perks": ["Full gym access", "Locker facility", "2 free fitness assessments", "Diet guidance"]},
    {"name": "Yearly", "label": "Yearly", "price": 12000, "period": "12 months",
     "perks": ["Full gym access", "Locker facility", "Quarterly assessments",
               "Diet guidance", "2 free personal training sessions"], "featured": True},
]

PLAN_MAP = {p["name"]: p for p in PLANS}

TRAINERS = [
    {"name": "Arjun", "role": "Head Coach", "focus": "Strength & Powerlifting", "icon": "🏋️"},
    {"name": "Priya", "role": "Fitness Trainer", "focus": "Weight Loss & HIIT", "icon": "🔥"},
    {"name": "Rahul", "role": "Conditioning Coach", "focus": "Functional & Mobility", "icon": "🤸"},
]

SCHEDULE = [
    {"time": "6:00 AM", "mon": "Strength", "tue": "HIIT", "wed": "Strength", "thu": "HIIT", "fri": "Strength", "sat": "Open Floor"},
    {"time": "8:00 AM", "mon": "Yoga", "tue": "Mobility", "wed": "Yoga", "thu": "Mobility", "fri": "Yoga", "sat": "Zumba"},
    {"time": "7:00 PM", "mon": "HIIT", "tue": "Strength", "wed": "Cardio", "thu": "Strength", "fri": "HIIT", "sat": "Open Floor"},
    {"time": "7:30 PM", "mon": "CrossFit", "tue": "Zumba", "wed": "CrossFit", "thu": "Zumba", "fri": "CrossFit", "sat": "-"},
]

TESTIMONIALS = [
    {"name": "Sneha K.", "text": "Lost 8 kg in 4 months. The trainers actually care about your progress."},
    {"name": "Vikram S.", "text": "Clean equipment, never overcrowded, and the yearly plan is great value."},
    {"name": "Meena R.", "text": "The evening HIIT classes completely changed my energy levels."},
]

# =========================================================
# GYM CONTACT DETAILS  (edit these - they appear on the website)
# =========================================================

SITE = {
    "name": "AGNI Fitness",
    "phone": "+91 70935 21131",
    "phone_link": "+917093521131",
    "email": "manishkumar76967498@gmail.com",
    "address": "3rd Cross, Sahakar Nagar, Hebbal, Bengaluru",
    "maps_url": "https://www.google.com/maps/search/?api=1&query=3rd+Cross+Sahakar+Nagar+Hebbal+Bengaluru",
    "hours": "Mon–Sat: 6:00 AM – 9:00 AM & 7:00 PM – 9:00 PM | Sun: Closed",
}


# Admin login comes from the .env file (never write the password in this file):
#   ADMIN_USERNAME=...
#   ADMIN_PASSWORD=...
# If they are missing, nobody can log in.
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    print("WARNING: ADMIN_USERNAME / ADMIN_PASSWORD are not set in .env - admin login is disabled.")


@app.context_processor
def inject_site():

    return {"site": SITE}


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html",
        plans=PLANS,
        trainers=TRAINERS,
        schedule=SCHEDULE,
        testimonials=TESTIMONIALS,
        site=SITE
    )


# =========================================================
# CONTACT FORM (public)
# =========================================================

def ensure_messages_table():

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()


@app.route("/contact", methods=["POST"])
def contact():

    name = request.form.get("name", "").strip()[:100]
    email = request.form.get("email", "").strip()[:150]
    message = request.form.get("message", "").strip()[:2000]

    if not name or not email or not message:
        return redirect(url_for("home", sent="error") + "#contact")

    ensure_messages_table()

    cursor.execute(
        "INSERT INTO contact_messages (name, email, message) VALUES (%s, %s, %s)",
        (name, email, message)
    )
    db.commit()

    return redirect(url_for("home", sent="ok") + "#contact")


@app.route("/admin/messages")
def admin_messages():

    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    ensure_messages_table()

    cursor.execute(
        "SELECT id, name, email, message, created_at "
        "FROM contact_messages ORDER BY created_at DESC"
    )
    rows = cursor.fetchall()

    return render_template("messages.html", messages=rows)


# =========================================================
# PAYMENT RECORDS
# Record what a member paid at the gym (cash / UPI / other).
# Uses its own table "payment_records" and its own database cursor,
# so it can never interfere with the rest of the site.
# =========================================================

PAYMENT_METHODS = {"cash": "Cash", "upi": "UPI", "other": "Other"}


def rec_cursor():

    # reconnect if MySQL dropped the connection, and end any old read snapshot
    try:
        db.ping(reconnect=True, attempts=2, delay=1)
        db.commit()
    except Exception:
        pass

    return db.cursor(buffered=True)


def ensure_payment_table():

    cur = rec_cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS payment_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                member_id INT NOT NULL,
                plan VARCHAR(30),
                amount INT NOT NULL,
                method VARCHAR(20) NOT NULL,
                note VARCHAR(100),
                paid_on DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
    finally:
        cur.close()


def describe_error(e):

    return "{}: {}".format(type(e).__name__, e)


def safe_next(value, default):

    # only allow going back to our own admin pages
    if value == "/admin/payments" or re.fullmatch(r"/view/\d+", value or ""):
        return value

    return default


@app.route("/admin/payments")
def admin_payments():

    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    today_d = date.today()

    month = request.args.get("month", "")

    try:
        first = datetime.strptime(month + "-01", "%Y-%m-%d").date()
    except ValueError:
        first = today_d.replace(day=1)

    month = first.strftime("%Y-%m")
    next_first = (first.replace(day=28) + timedelta(days=4)).replace(day=1)

    rows = []
    member_options = []
    today_total = 0
    all_time = 0
    error = None

    try:

        ensure_payment_table()

        cur = rec_cursor()

        try:

            cur.execute(
                """
                SELECT p.id, p.member_id,
                       COALESCE(m.name, '(deleted member)'),
                       p.plan, p.amount, p.method, p.note, p.paid_on
                FROM payment_records p
                LEFT JOIN members m ON m.id = p.member_id
                WHERE p.paid_on >= %s AND p.paid_on < %s
                ORDER BY p.paid_on DESC, p.id DESC
                """,
                (first, next_first)
            )
            rows = cur.fetchall()

            cur.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM payment_records "
                "WHERE paid_on = %s",
                (today_d,)
            )
            today_total = int(cur.fetchall()[0][0])

            cur.execute("SELECT COALESCE(SUM(amount), 0) FROM payment_records")
            all_time = int(cur.fetchall()[0][0])

            cur.execute("SELECT id, name, phone, membership FROM members ORDER BY name")

            for m in cur.fetchall():
                plan_info = PLAN_MAP.get(m[3])
                member_options.append({
                    "id": m[0],
                    "name": m[1],
                    "phone": m[2],
                    "plan": m[3],
                    "price": plan_info["price"] if plan_info else ""
                })

        finally:
            cur.close()

    except Exception as e:

        app.logger.exception("payments page failed")
        error = describe_error(e)

    month_total = sum(r[4] for r in rows)
    cash_total = sum(r[4] for r in rows if r[5] == "cash")
    upi_total = sum(r[4] for r in rows if r[5] == "upi")

    return render_template(
        "payments.html",
        payments=rows,
        members=member_options,
        month=month,
        month_label=first.strftime("%B %Y"),
        today=today_d.isoformat(),
        today_total=today_total,
        all_time=all_time,
        month_total=month_total,
        cash_total=cash_total,
        upi_total=upi_total,
        methods=PAYMENT_METHODS,
        error=error
    )


@app.route("/admin/payments/add", methods=["POST"])
def add_payment():

    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    back = safe_next(
        request.form.get("next", ""),
        url_for("admin_payments")
    )

    # ---- check the form
    try:
        member_id = int(request.form.get("member_id", ""))
    except ValueError:
        flash("Please choose a member.", "err")
        return redirect(back)

    try:
        amount = int(request.form.get("amount", "").strip())
    except ValueError:
        flash("Please enter the amount as a whole number, for example 1500.", "err")
        return redirect(back)

    if not 1 <= amount <= 1000000:
        flash("The amount must be between 1 and 10,00,000.", "err")
        return redirect(back)

    method = request.form.get("method", "cash")

    if method not in PAYMENT_METHODS:
        flash("Please choose Cash, UPI or Other.", "err")
        return redirect(back)

    try:
        paid_on = parse_date(request.form.get("paid_on", ""))
    except ValueError:
        flash("Please pick a valid payment date.", "err")
        return redirect(back)

    if paid_on > date.today():
        flash("The payment date cannot be in the future.", "err")
        return redirect(back)

    note = request.form.get("note", "").strip()[:100] or None

    # ---- save it
    try:

        ensure_payment_table()

        cur = rec_cursor()

        try:

            cur.execute(
                "SELECT membership FROM members WHERE id = %s",
                (member_id,)
            )
            found = cur.fetchall()

            if not found:
                flash("That member no longer exists.", "err")
                return redirect(back)

            cur.execute(
                "INSERT INTO payment_records "
                "(member_id, plan, amount, method, note, paid_on) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (member_id, found[0][0], amount, method, note, paid_on)
            )
            db.commit()

        finally:
            cur.close()

    except Exception as e:

        app.logger.exception("saving payment failed")
        flash("Could not save the payment - " + describe_error(e), "err")
        return redirect(back)

    flash("Payment of ₹{:,} recorded.".format(amount), "ok")

    return redirect(back)


@app.route("/admin/payments/<int:payment_id>/delete", methods=["POST"])
def delete_payment(payment_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    back = safe_next(
        request.form.get("next", ""),
        url_for("admin_payments")
    )

    try:

        ensure_payment_table()

        cur = rec_cursor()

        try:
            cur.execute(
                "DELETE FROM payment_records WHERE id = %s",
                (payment_id,)
            )
            db.commit()
        finally:
            cur.close()

    except Exception as e:

        app.logger.exception("deleting payment failed")
        flash("Could not delete the payment - " + describe_error(e), "err")
        return redirect(back)

    flash("Payment deleted.", "ok")

    return redirect(back)


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if (
            ADMIN_USERNAME and ADMIN_PASSWORD
            and secrets.compare_digest(username.encode(), ADMIN_USERNAME.encode())
            and secrets.compare_digest(password.encode(), ADMIN_PASSWORD.encode())
        ):

            session["admin_logged_in"] = True

            return redirect(
                url_for("admin")
            )

        else:

            return render_template(
                "login.html",
                error="Invalid username or password!"
            )

    return render_template(
        "login.html",
        today=date.today().isoformat()
    )


# =========================================================
# REGISTER MEMBER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    error = None

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        membership = request.form.get("membership", "")
        start_date = request.form.get("start_date", "").strip()

        months = {"Monthly": 1, "3 Months": 3, "6 Months": 6, "Yearly": 12}

        start = None

        if not name or not email or not phone:

            error = "Please fill in your name, email and phone number."

        elif membership not in months:

            error = "Please select a membership plan."

        else:

            try:
                start = parse_date(start_date)
            except ValueError:
                error = "Please pick a valid start date."

        if not error:

            expiry = add_months(start, months[membership])

            try:

                cursor.execute(
                    """
                    INSERT INTO members
                    (name, email, phone, membership, start_date, expiry_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (name, email, phone, membership, start, expiry)
                )

                db.commit()

            except Exception:

                app.logger.exception("registration failed")

                try:
                    db.rollback()
                except Exception:
                    pass

                error = (
                    "Sorry, we could not save your registration right now. "
                    "Please try again, or visit the front desk."
                )

            else:

                return redirect(
                    url_for(
                        "register_success",
                        name=name,
                        plan=membership,
                        start=start.strftime("%d-%m-%Y"),
                        expiry=expiry.strftime("%d-%m-%Y")
                    )
                )

    return render_template(
        "register.html",
        today=date.today().isoformat(),
        plans=PLANS,
        error=error,
        form=request.form
    )


@app.route("/register/success")
def register_success():

    plan = request.args.get("plan", "")

    plan_info = PLAN_MAP.get(plan)

    return render_template(
        "register_success.html",
        name=request.args.get("name", ""),
        plan=plan,
        start=request.args.get("start", ""),
        expiry=request.args.get("expiry", ""),
        fee=plan_info["price"] if plan_info else None
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin():

    # =====================================================
    # PROTECT DASHBOARD
    # =====================================================

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("login")
        )


    # =====================================================
    # SEARCH
    # =====================================================

    search = request.args.get(
        "search",
        ""
    )


    # =====================================================
    # PAGINATION
    # =====================================================

    page = request.args.get(
        "page",
        1,
        type=int
    )

    per_page = request.args.get(
        "per_page",
        10,
        type=int
    )

    if page < 1:

        page = 1

    if per_page not in [
        10,
        25,
        50,
        100
    ]:

        per_page = 10


    # =====================================================
    # STATUS FILTER
    # =====================================================

    status_filter = request.args.get(
        "status",
        "all"
    )


    # =====================================================
    # SORTING
    # =====================================================

    sort = request.args.get(
        "sort",
        "default"
    )


    # =====================================================
    # BASE SQL
    # =====================================================

    sql = """
    SELECT
        *,

        CASE

            WHEN expiry_date IS NULL
                THEN 'No Membership'

            WHEN start_date > CURDATE()
                THEN 'Upcoming'

            WHEN expiry_date < CURDATE()
                THEN 'Expired'

            ELSE 'Active'

        END AS status,

        CASE

            WHEN expiry_date IS NULL
                THEN NULL

            WHEN start_date > CURDATE()
                THEN DATEDIFF(
                    start_date,
                    CURDATE()
                )

            WHEN expiry_date >= CURDATE()
                THEN DATEDIFF(
                    expiry_date,
                    CURDATE()
                )

            ELSE NULL

        END AS days_remaining

    FROM members
    """


    conditions = []
    values = []


    # =====================================================
    # SEARCH
    # =====================================================

    if search:

        conditions.append("""
            (
                name LIKE %s
                OR email LIKE %s
                OR phone LIKE %s
            )
        """)

        search_value = "%" + search + "%"

        values.extend([
            search_value,
            search_value,
            search_value
        ])


    # =====================================================
    # STATUS FILTER
    # =====================================================

    if status_filter == "active":

        conditions.append("""
            start_date <= CURDATE()
            AND expiry_date >= CURDATE()
        """)

    elif status_filter == "upcoming":

        conditions.append("""
            start_date > CURDATE()
        """)

    elif status_filter == "expiring":

        conditions.append("""
            start_date <= CURDATE()
            AND expiry_date >= CURDATE()
            AND expiry_date <= DATE_ADD(
                CURDATE(),
                INTERVAL 30 DAY
            )
        """)

    elif status_filter == "expired":

        conditions.append("""
            expiry_date < CURDATE()
        """)


    # =====================================================
    # WHERE
    # =====================================================

    if conditions:

        sql += (
            " WHERE " +
            " AND ".join(conditions)
        )


    # =====================================================
    # SORTING
    # =====================================================

    if sort == "name_asc":

        sql += """
        ORDER BY name ASC
        """

    elif sort == "name_desc":

        sql += """
        ORDER BY name DESC
        """

    elif sort == "expiry_soon":

        sql += """
        ORDER BY
            expiry_date IS NULL,
            expiry_date ASC
        """

    elif sort == "expiry_late":

        sql += """
        ORDER BY
            expiry_date IS NULL,
            expiry_date DESC
        """

    elif sort == "newest":

        sql += """
        ORDER BY id DESC
        """

    elif sort == "oldest":

        sql += """
        ORDER BY id ASC
        """

    else:

        sql += """
        ORDER BY id ASC
        """


    # =====================================================
    # COUNT FILTERED RESULTS
    # =====================================================

    count_sql = """
    SELECT COUNT(*)
    FROM members
    """

    count_values = list(values)


    if conditions:

        count_sql += (
            " WHERE " +
            " AND ".join(conditions)
        )


    cursor.execute(
        count_sql,
        count_values
    )

    total_filtered = cursor.fetchone()[0]


    # =====================================================
    # TOTAL PAGES
    # =====================================================

    if total_filtered == 0:

        total_pages = 1

    else:

        total_pages = (
            total_filtered +
            per_page -
            1
        ) // per_page


    # =====================================================
    # FIX INVALID PAGE
    # =====================================================

    if page > total_pages:

        page = total_pages


    offset = (
        page - 1
    ) * per_page


    # =====================================================
    # PAGINATION
    # =====================================================

    sql += """
    LIMIT %s OFFSET %s
    """

    values.extend([
        per_page,
        offset
    ])


    # =====================================================
    # GET MEMBERS
    # =====================================================

    cursor.execute(
        sql,
        values
    )
    members = cursor.fetchall()


    # =====================================================
    # TODAY'S ATTENDANCE
    # =====================================================

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM attendance
        WHERE attendance_date = CURDATE()
        """
    )

    today_attendance = cursor.fetchone()[0] or 0


    # =====================================================
    # THIS WEEK'S ATTENDANCE
    # =====================================================

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM attendance
        WHERE YEARWEEK(attendance_date, 1)
              = YEARWEEK(CURDATE(), 1)
        """
    )

    weekly_attendance = cursor.fetchone()[0] or 0

    # =====================================================
    # DASHBOARD COUNTS
    # =====================================================

    cursor.execute("""
        SELECT

            COUNT(*),

            SUM(
                CASE
                    WHEN start_date <= CURDATE()
                    AND expiry_date >= CURDATE()
                    THEN 1
                    ELSE 0
                END
            ),

            SUM(
                CASE
                    WHEN start_date <= CURDATE()
                    AND expiry_date >= CURDATE()
                    AND expiry_date <= DATE_ADD(
                        CURDATE(),
                        INTERVAL 30 DAY
                    )
                    THEN 1
                    ELSE 0
                END
            ),

            SUM(
                CASE
                    WHEN expiry_date < CURDATE()
                    THEN 1
                    ELSE 0
                END
            ),

            SUM(
                CASE
                    WHEN start_date > CURDATE()
                    THEN 1
                    ELSE 0
                END
            )

        FROM members
    """)


    counts = cursor.fetchone()


    member_count = (
        counts[0] or 0
    )

    active_count = (
        counts[1] or 0
    )

    expiring_count = (
        counts[2] or 0
    )

    expired_count = (
        counts[3] or 0
    )

    upcoming_count = (
        counts[4] or 0
    )


    # =====================================================
    # EXPIRING SOON
    # =====================================================

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            phone,
            membership,
            start_date,
            expiry_date

        FROM members

        WHERE start_date <= CURDATE()

        AND expiry_date >= CURDATE()

        AND expiry_date <= DATE_ADD(
            CURDATE(),
            INTERVAL 30 DAY
        )

        ORDER BY expiry_date ASC
    """)


    expiring_members = cursor.fetchall()


    # =====================================================
    # MEMBERSHIP DISTRIBUTION
    # =====================================================

    cursor.execute("""
        SELECT
            membership,
            COUNT(*)

        FROM members

        GROUP BY membership
    """)


    membership_counts = cursor.fetchall()


    monthly_count = 0
    three_month_count = 0
    six_month_count = 0
    yearly_count = 0


    for membership, count in membership_counts:

        if membership == "Monthly":

            monthly_count = count

        elif membership == "3 Months":

            three_month_count = count

        elif membership == "6 Months":

            six_month_count = count

        elif membership == "Yearly":

            yearly_count = count


    # =====================================================
    # SEND DATA TO TEMPLATE
    # =====================================================

    return render_template(

        "admin.html",

        members=members,

        member_count=member_count,

        active_count=active_count,

        expiring_count=expiring_count,

        expired_count=expired_count,

        upcoming_count=upcoming_count,

        today_attendance=today_attendance,

        weekly_attendance=weekly_attendance,

        monthly_count=monthly_count,

        three_month_count=three_month_count,

        six_month_count=six_month_count,

        yearly_count=yearly_count,

        search=search,

        status_filter=status_filter,

        sort=sort,

        expiring_members=expiring_members,

        today=date.today(),

        page=page,

        per_page=per_page,

        total_pages=total_pages,

        total_filtered=total_filtered
    )

# =========================================================
# TODAY'S ATTENDANCE
# =========================================================

@app.route("/attendance/today")
def today_attendance_page():

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("login")
        )


    cursor.execute(
        """
        SELECT
            members.id,
            members.name,
            members.phone,
            attendance.attendance_date,
            attendance.attendance_time

        FROM attendance

        INNER JOIN members
            ON attendance.member_id = members.id

        WHERE attendance.attendance_date = CURDATE()

        ORDER BY
            attendance.attendance_time DESC
        """
    )


    today_attendance_records = cursor.fetchall()


    return render_template(
        "today_attendance.html",
        attendance_records=today_attendance_records,
        today=date.today()
    )
# =========================================================
# WEEKLY ATTENDANCE
# =========================================================

@app.route("/attendance/weekly")
def weekly_attendance_page():

    if not session.get("admin_logged_in"):
        return redirect(
            url_for("login")
        )

    selected_date = request.args.get("date")

    if selected_date:
        try:
            selected_date_obj = datetime.strptime(
                selected_date,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            selected_date_obj = date.today()
    else:
        selected_date_obj = date.today()

    cursor.execute(
        """
        SELECT
            members.id,
            members.name,
            members.phone,
            attendance.attendance_date,
            attendance.attendance_time

        FROM attendance

        INNER JOIN members
            ON attendance.member_id = members.id

        WHERE attendance.attendance_date = %s

        ORDER BY attendance.attendance_time DESC
        """,
        (selected_date_obj,)
    )

    attendance_records = cursor.fetchall()

    return render_template(
        "weekly_attendance.html",
        attendance_records=attendance_records,
        selected_date=selected_date_obj
    )
# =========================================================

# =========================================================
# VIEW MEMBER
# =========================================================

@app.route("/view/<int:id>")
def view_member(id):

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("login")
        )


    cursor.execute(
        """
        SELECT
            *,

            CASE

                WHEN expiry_date IS NULL
                    THEN 'No Membership'

                WHEN start_date > CURDATE()
                    THEN 'Upcoming'

                WHEN expiry_date < CURDATE()
                    THEN 'Expired'

                ELSE 'Active'

            END AS status,

            CASE

                WHEN expiry_date IS NULL
                    THEN NULL

                WHEN start_date > CURDATE()
                    THEN DATEDIFF(
                        start_date,
                        CURDATE()
                    )

                WHEN expiry_date >= CURDATE()
                    THEN DATEDIFF(
                        expiry_date,
                        CURDATE()
                    )

                ELSE NULL

            END AS days_remaining

        FROM members

        WHERE id = %s
        """,

        (id,)
    )


    member = cursor.fetchone()


    if member is None:

        return (
            "Member not found",
            404
        )


    # =====================================================
    # ATTENDANCE HISTORY
    # =====================================================

    cursor.execute(
        """
        SELECT
            attendance_date,
            attendance_time

        FROM attendance

        WHERE member_id = %s

        ORDER BY
            attendance_date DESC,
            attendance_time DESC
        """,

        (id,)
    )

    attendance_history = cursor.fetchall()


    # =====================================================
    # ATTENDANCE SUMMARY
    # =====================================================

    cursor.execute(
        """
        SELECT
            COUNT(*),
            SUM(
                CASE
                    WHEN YEAR(attendance_date) = YEAR(CURDATE())
                    AND MONTH(attendance_date) = MONTH(CURDATE())
                    THEN 1
                    ELSE 0
                END
            ),
            SUM(
                CASE
                    WHEN YEARWEEK(attendance_date, 1)
                         = YEARWEEK(CURDATE(), 1)
                    THEN 1
                    ELSE 0
                END
            ),
            MAX(attendance_date)
        FROM attendance
        WHERE member_id = %s
        """,
        (id,)
    )

    attendance_summary = cursor.fetchone()
    # =====================================================
    # CHECK TODAY'S ATTENDANCE
    # =====================================================

    today_attendance = False


    for attendance_date, attendance_time in attendance_history:

        if attendance_date == date.today():

            today_attendance = True

            break

    # ATTENDANCE SUMMARY
    # =====================================================

    total_attendance = len(
        attendance_history
    )


    if attendance_history:

        last_attendance_date = (
            attendance_history[0][0]
        )

        last_attendance_time = (
            attendance_history[0][1]
        )

    else:

        last_attendance_date = None
        last_attendance_time = None


    # =====================================================
    # FORMAT ATTENDANCE TIME
    # =====================================================

    formatted_attendance_history = []


    for attendance_date, attendance_time in attendance_history:

        total_seconds = int(
            attendance_time.total_seconds()
        )

        hours = total_seconds // 3600

        minutes = (
            total_seconds % 3600
        ) // 60


        formatted_time = (
            f"{hours % 12 or 12:02d}:"
            f"{minutes:02d} "
            f"{'AM' if hours < 12 else 'PM'}"
        )


        formatted_attendance_history.append(
            (
                attendance_date,
                formatted_time
            )
        )


    # =====================================================
    # PAYMENT HISTORY + REGULARITY
    # =====================================================

    payment_rows = []
    payment_error = None

    try:

        ensure_payment_table()

        pcur = rec_cursor()

        try:

            pcur.execute(
                """
                SELECT id, plan, amount, method, note, paid_on
                FROM payment_records
                WHERE member_id = %s
                ORDER BY paid_on DESC, id DESC
                """,
                (id,)
            )

            payment_rows = pcur.fetchall()

        finally:
            pcur.close()

    except Exception as e:

        app.logger.exception("member payment history failed")
        payment_error = describe_error(e)

    today_d = date.today()
    start_d = member[5]

    total_paid = sum(r[2] for r in payment_rows)

    paid_last_30 = sum(
        r[2] for r in payment_rows
        if (today_d - r[5]).days < 30
    )

    last_payment = payment_rows[0] if payment_rows else None

    plan_info = PLAN_MAP.get(member[4])
    plan_price = plan_info["price"] if plan_info else None

    # payments counted for the CURRENT plan: from 14 days before it started
    if start_d:
        plan_paid = sum(
            r[2] for r in payment_rows
            if (r[5] - start_d).days >= -14
        )
    else:
        plan_paid = total_paid

    if plan_price:
        if plan_paid >= plan_price:
            plan_state = "paid"
        elif plan_paid > 0:
            plan_state = "part"
        else:
            plan_state = "none"
    else:
        plan_state = "paid" if plan_paid > 0 else "none"

    # attendance regularity: visit days per week (looking at up to the last 30 days)
    if start_d is None or start_d > today_d:
        regularity = {"label": "Not started", "visits": 0, "days": 0, "per_week": 0}
    else:
        window = max(1, min(30, (today_d - start_d).days + 1))
        visit_days = {
            d for d, t in attendance_history
            if 0 <= (today_d - d).days < window
        }
        visits = len(visit_days)
        per_week = round(visits / (window / 7.0), 1)

        if window < 7:
            label = "Too new to tell"
        elif per_week >= 3:
            label = "Regular"
        elif per_week >= 1:
            label = "Occasional"
        else:
            label = "Rarely attends"

        regularity = {
            "label": label,
            "visits": visits,
            "days": window,
            "per_week": per_week
        }

    # =====================================================
    # RETURN MEMBER DETAILS
    # =====================================================

    return render_template(

        "member_details.html",

        member=member,

        attendance_history=formatted_attendance_history,

        total_attendance=total_attendance,

        last_attendance_date=last_attendance_date,

        last_attendance_time=last_attendance_time,

        today_attendance=today_attendance,

        

        attendance_already_marked=request.args.get(
            "attendance_already_marked"
        ),
        attendance_summary=attendance_summary,

        payment_rows=payment_rows,
        payment_error=payment_error,
        total_paid=total_paid,
        paid_last_30=paid_last_30,
        last_payment=last_payment,
        plan_price=plan_price,
        plan_paid=plan_paid,
        plan_state=plan_state,
        methods=PAYMENT_METHODS,
        today=today_d.isoformat(),
        regularity=regularity

    )

# =============================
# EDIT MEMBER
# =============================

@app.route(
    "/edit/<int:id>",
    methods=["GET", "POST"]
)
def edit(id):

    # =====================================================
    # PROTECT ADMIN
    # =====================================================

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("login")
        )


    # =====================================================
    # UPDATE MEMBER
    # =====================================================

    if request.method == "POST":

        name = request.form[
            "name"
        ].strip()

        email = request.form[
            "email"
        ].strip()

        phone = request.form[
            "phone"
        ].strip()

        membership = request.form[
            "membership"
        ]

        start_date = request.form[
            "start_date"
        ].strip()


        # =================================================
        # DATE
        # =================================================

        try:

            start = parse_date(
                start_date
            )

        except ValueError:

            return (
                "Invalid date. Please select a valid date.",
                400
            )


        # =================================================
        # EXPIRY
        # =================================================

        if membership == "Monthly":

            expiry = add_months(
                start,
                1
            )

        elif membership == "3 Months":

            expiry = add_months(
                start,
                3
            )

        elif membership == "6 Months":

            expiry = add_months(
                start,
                6
            )

        elif membership == "Yearly":

            expiry = add_months(
                start,
                12
            )

        else:

            return (
                "Invalid membership type",
                400
            )


        # =================================================
        # UPDATE DATABASE
        # =================================================

        sql = """
        UPDATE members

        SET
            name = %s,
            email = %s,
            phone = %s,
            membership = %s,
            start_date = %s,
            expiry_date = %s

        WHERE id = %s
        """


        values = (
            name,
            email,
            phone,
            membership,
            start,
            expiry,
            id
        )


        cursor.execute(
            sql,
            values
        )

        db.commit()


        return redirect(
            url_for("admin") + "#members"
        )


    # =====================================================
    # GET MEMBER
    # =====================================================

    cursor.execute(
        """
        SELECT *
        FROM members
        WHERE id = %s
        """,

        (id,)
    )


    member = cursor.fetchone()


    if member is None:

        return (
            "Member not found",
            404
        )


    return render_template(
        "edit.html",
        member=member
    )


# =========================================================
# DELETE MEMBER
# =========================================================

@app.route(
    "/delete/<int:id>",
    methods=["POST"]
)
def delete(id):

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("login")
        )


    cursor.execute(
        """
        DELETE FROM members
        WHERE id = %s
        """,

        (id,)
    )


    db.commit()


    return redirect(
        url_for("admin") + "#members"
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.pop(
        "admin_logged_in",
        None
    )


    return redirect(
        url_for("login")
    )
@app.route("/mark_attendance/<int:id>")
def mark_attendance(id):

    # Protect admin
    if not session.get("admin_logged_in"):
        return redirect( 
            url_for("login")
        ) 


    # =====================================================
    # CHECK MEMBER EXISTS
    # =====================================================

    cursor.execute(
        """
        SELECT id
        FROM members
        WHERE id = %s
        """,
        (id,)
    )

    member = cursor.fetchone()

    if member is None:

        return (
            "Member not found",
            404
        )


    # =====================================================
    # CHECK TODAY'S ATTENDANCE
    # =====================================================

    cursor.execute(
        """
        SELECT id
        FROM attendance
        WHERE member_id = %s
        AND attendance_date = CURDATE()
        """,
        (id,)
    )

    already_marked = cursor.fetchone()


    # =====================================================
    # PREVENT DUPLICATE ATTENDANCE
    # =====================================================

    if already_marked:
     return redirect(
        url_for(
            "view_member",
            id=id,
            attendance_already_marked=1
        )
    )


    # =====================================================
    # MARK ATTENDANCE
    # =====================================================

    cursor.execute(
        """
        INSERT INTO attendance
        (
            member_id,
            attendance_date,
            attendance_time
        )
        VALUES
        (
            %s,
            CURDATE(),
            CURTIME()
        )
        """,
        (id,)
    )

    db.commit()


    # =====================================================
    # RETURN TO MEMBER DETAILS
    # =====================================================

    return redirect(
        url_for(
            "view_member",
            id=id
        )
    )
# =========================================================
# RUN FLASK
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )