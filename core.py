"""Core logic and database for the Student Planner app (no GUI code here)."""
import re
import sqlite3
from datetime import date, datetime, timedelta

DB_FILE = "planner.db"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
NOTIFY_HOUR = 19  # 7:00 PM


def set_db_file(path):
    """Point the whole app (and the background service) at one database file."""
    global DB_FILE
    DB_FILE = path


def connect(path=None):
    return sqlite3.connect(path or DB_FILE, timeout=10)


def init_db(path=None):
    with connect(path) as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS timetable (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL,
                start_time TEXT NOT NULL,
                subject TEXT NOT NULL,
                items TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT '',
                deadline TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )


# ---------- timetable ----------
def add_class(day, start_time, subject, items, path=None):
    if day not in DAYS:
        raise ValueError("Choose a valid day.")
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", start_time.strip()):
        raise ValueError("Time must be HH:MM (24-hour), e.g. 09:30.")
    if not subject.strip():
        raise ValueError("Subject cannot be empty.")
    with connect(path) as c:
        c.execute(
            "INSERT INTO timetable (day, start_time, subject, items) VALUES (?,?,?,?)",
            (day, start_time.strip(), subject.strip(), items.strip()),
        )


def get_classes(day, path=None):
    with connect(path) as c:
        return c.execute(
            "SELECT id, start_time, subject, items FROM timetable WHERE day=? ORDER BY start_time",
            (day,),
        ).fetchall()


def delete_class(class_id, path=None):
    with connect(path) as c:
        c.execute("DELETE FROM timetable WHERE id=?", (class_id,))


def items_for_day(day, path=None):
    """Return {item: [subjects that need it]} for a weekday, de-duplicated."""
    result = {}
    names = {}
    for _id, _t, subject, items in get_classes(day, path):
        for raw in items.split(","):
            item = raw.strip()
            if not item:
                continue
            key = item.lower()
            names.setdefault(key, item)
            result.setdefault(key, [])
            if subject not in result[key]:
                result[key].append(subject)
    return {names[k]: v for k, v in result.items()}


# ---------- assignments ----------
def parse_date(text):
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Deadline must be YYYY-MM-DD, e.g. 2026-10-25.")


def add_assignment(title, subject, deadline, path=None):
    if not title.strip():
        raise ValueError("Title cannot be empty.")
    d = parse_date(deadline)
    with connect(path) as c:
        c.execute(
            "INSERT INTO assignments (title, subject, deadline) VALUES (?,?,?)",
            (title.strip(), subject.strip(), d.isoformat()),
        )


def list_assignments(path=None):
    with connect(path) as c:
        return c.execute(
            "SELECT id, title, subject, deadline, done FROM assignments ORDER BY done, deadline"
        ).fetchall()


def toggle_done(assignment_id, path=None):
    with connect(path) as c:
        c.execute("UPDATE assignments SET done = 1 - done WHERE id=?", (assignment_id,))


def delete_assignment(assignment_id, path=None):
    with connect(path) as c:
        c.execute("DELETE FROM assignments WHERE id=?", (assignment_id,))


def assignments_due_on(target, path=None):
    with connect(path) as c:
        return c.execute(
            "SELECT title, subject FROM assignments WHERE deadline=? AND done=0",
            (target.isoformat(),),
        ).fetchall()


# ---------- settings / reminders ----------
def get_setting(key, default=None, path=None):
    with connect(path) as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_setting(key, value, path=None):
    with connect(path) as c:
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))


def build_reminder(target, path=None):
    """Message for the given date (normally tomorrow)."""
    day = DAYS[target.weekday()]
    items = items_for_day(day, path)
    due = assignments_due_on(target, path)
    lines = []
    if items:
        lines.append(f"Pack for {day}:")
        for item, subjects in items.items():
            lines.append(f"  - {item} ({', '.join(subjects)})")
    else:
        lines.append(f"No classes/items scheduled for {day}.")
    if due:
        lines.append("")
        lines.append("Assignments due tomorrow:")
        for title, subject in due:
            lines.append(f"  - {title}" + (f" ({subject})" if subject else ""))
    return f"Tomorrow's checklist - {day}", "\n".join(lines)


def reminder_due(now=None, path=None):
    """True if it is >= 7 PM and today's reminder hasn't been sent yet."""
    now = now or datetime.now()
    if now.hour < NOTIFY_HOUR:
        return False
    return get_setting("last_notified", path=path) != now.date().isoformat()


def mark_reminder_sent(now=None, path=None):
    now = now or datetime.now()
    set_setting("last_notified", now.date().isoformat(), path)


def tomorrow(now=None):
    return (now or datetime.now()).date() + timedelta(days=1)
