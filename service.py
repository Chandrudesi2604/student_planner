"""Background service: checks the time and sends the 7 PM reminder once per day.

Runs as an Android foreground service (see buildozer.spec), so it keeps working
after the app screen is closed.
"""
import time

import core
from notify import db_path, send_notification


def main():
    core.set_db_file(db_path())
    core.init_db()
    while True:
        try:
            if core.reminder_due():
                core.mark_reminder_sent()
                title, message = core.build_reminder(core.tomorrow())
                send_notification(title, message)
        except Exception as exc:
            print("service error:", exc)
        time.sleep(30)


if __name__ == "__main__":
    main()
