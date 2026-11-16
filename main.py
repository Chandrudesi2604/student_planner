"""Student Planner (Kivy) - timetable, daily bag checklist, assignments, 7 PM reminders.

Works on Android (build with Buildozer) and on a desktop for testing:
    python main.py
"""
from datetime import date

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.textinput import TextInput

import core
import notify

Window.softinput_mode = "below_target"  # keep inputs visible above the keyboard


def show_message(title, text):
    box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
    lbl = Label(text=text, halign="left", valign="top")
    lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
    box.add_widget(lbl)
    btn = Button(text="OK", size_hint_y=None, height=dp(44))
    box.add_widget(btn)
    pop = Popup(title=title, content=box, size_hint=(0.9, 0.6))
    btn.bind(on_release=pop.dismiss)
    pop.open()


def field(hint, text="", **kw):
    return TextInput(hint_text=hint, text=text, multiline=False, write_tab=False,
                     size_hint_y=None, height=dp(42), **kw)


class ScrollList(ScrollView):
    """A vertical list of rows that can be cleared and refilled."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        self.box.bind(minimum_height=self.box.setter("height"))
        self.add_widget(self.box)

    def clear(self):
        self.box.clear_widgets()

    def add_row(self, widget):
        self.box.add_widget(widget)


def wrapped_label(text, height=None, **kw):
    lbl = Label(text=text, halign="left", valign="middle", **kw)
    lbl.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
    lbl.bind(texture_size=lambda w, s: setattr(w, "height", max(dp(36), s[1] + dp(8))))
    lbl.size_hint_y = None
    lbl.height = height or dp(36)
    return lbl


class PlannerRoot(TabbedPanel):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.do_default_tab = False
        self.tab_width = dp(120)
        self.build_bag_tab()
        self.build_timetable_tab()
        self.build_assignment_tab()
        self.refresh_all()

    # ---------------- Pack My Bag ----------------
    def build_bag_tab(self):
        tab = TabbedPanelItem(text="Pack Bag")
        root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
        self.bag_day = Spinner(text=core.DAYS[date.today().weekday()], values=core.DAYS)
        self.bag_day.bind(text=lambda *a: self.refresh_bag())
        today_btn = Button(text="Today", size_hint_x=0.4)
        tomorrow_btn = Button(text="Tomorrow", size_hint_x=0.5)
        today_btn.bind(on_release=lambda *a: self.set_bag_day(0))
        tomorrow_btn.bind(on_release=lambda *a: self.set_bag_day(1))
        for w in (self.bag_day, today_btn, tomorrow_btn):
            top.add_widget(w)
        root.add_widget(top)

        self.bag_list = ScrollList()
        root.add_widget(self.bag_list)

        test_btn = Button(text="Send test reminder now", size_hint_y=None, height=dp(44))
        test_btn.bind(on_release=lambda *a: self.send_test_reminder())
        root.add_widget(test_btn)
        tab.add_widget(root)
        self.add_widget(tab)
        self.default_tab = tab

    def set_bag_day(self, offset):
        self.bag_day.text = core.DAYS[(date.today().weekday() + offset) % 7]

    def refresh_bag(self):
        day = self.bag_day.text
        self.bag_list.clear()
        self.bag_list.add_row(wrapped_label(f"[b]Suggested bag for {day}[/b]", markup=True,
                                            font_size=dp(18)))
        classes = core.get_classes(day)
        if not classes:
            self.bag_list.add_row(wrapped_label("No classes in the timetable for this day."))
        else:
            self.bag_list.add_row(wrapped_label("[b]Classes[/b]", markup=True))
            for _cid, start, subject, _items in classes:
                self.bag_list.add_row(wrapped_label(f"   {start}  {subject}"))
            self.bag_list.add_row(wrapped_label("[b]Take these items[/b]", markup=True))
            items = core.items_for_day(day)
            if items:
                for item, subjects in items.items():
                    self.bag_list.add_row(wrapped_label(f"   [ ]  {item}   ({', '.join(subjects)})"))
            else:
                self.bag_list.add_row(wrapped_label("   (no items recorded)"))
        today = date.today()
        soon = [a for a in core.list_assignments()
                if not a[4] and (core.parse_date(a[3]) - today).days in (0, 1)]
        if soon:
            self.bag_list.add_row(wrapped_label("[b]Assignments due today/tomorrow[/b]", markup=True))
            for _aid, title, _subject, deadline, _done in soon:
                self.bag_list.add_row(wrapped_label(f"   !  {title}  (due {deadline})"))

    def send_test_reminder(self):
        title, message = core.build_reminder(core.tomorrow())
        if not notify.send_notification(title, message, notif_id=2):
            show_message(title, message)  # desktop / notification blocked

    # ---------------- Timetable ----------------
    def build_timetable_tab(self):
        tab = TabbedPanelItem(text="Timetable")
        root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(4))
        row1 = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
        self.tt_day = Spinner(text=core.DAYS[0], values=core.DAYS, size_hint_x=0.55)
        self.tt_time = field("HH:MM", "09:00", size_hint_x=0.45)
        row1.add_widget(self.tt_day)
        row1.add_widget(self.tt_time)
        self.tt_subject = field("Subject")
        self.tt_items = field("Items needed (comma separated)")
        add = Button(text="Add class", size_hint_y=None, height=dp(44))
        add.bind(on_release=lambda *a: self.add_class())
        for w in (row1, self.tt_subject, self.tt_items, add):
            root.add_widget(w)
        self.tt_list = ScrollList()
        root.add_widget(self.tt_list)
        tab.add_widget(root)
        self.add_widget(tab)

    def add_class(self):
        try:
            core.add_class(self.tt_day.text, self.tt_time.text,
                           self.tt_subject.text, self.tt_items.text)
        except ValueError as exc:
            show_message("Invalid input", str(exc))
            return
        self.tt_subject.text = ""
        self.tt_items.text = ""
        self.refresh_all()

    def refresh_timetable(self):
        self.tt_list.clear()
        for day in core.DAYS:
            rows = core.get_classes(day)
            if not rows:
                continue
            self.tt_list.add_row(wrapped_label(f"[b]{day}[/b]", markup=True, color=(0.4, 0.7, 1, 1)))
            for cid, start, subject, items in rows:
                row = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(4))
                text = f"{start}  {subject}" + (f"\n[size=13sp]{items}[/size]" if items else "")
                lbl = Label(text=text, markup=True, halign="left", valign="middle")
                lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
                delete = Button(text="Delete", size_hint_x=None, width=dp(80))
                delete.bind(on_release=lambda _b, c=cid: self.delete_class(c))
                row.add_widget(lbl)
                row.add_widget(delete)
                self.tt_list.add_row(row)

    def delete_class(self, class_id):
        core.delete_class(class_id)
        self.refresh_all()

    # ---------------- Assignments ----------------
    def build_assignment_tab(self):
        tab = TabbedPanelItem(text="Assignments")
        root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(4))
        self.as_title = field("Assignment title")
        row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
        self.as_subject = field("Subject", size_hint_x=0.45)
        self.as_deadline = field("YYYY-MM-DD", date.today().isoformat(), size_hint_x=0.55)
        row.add_widget(self.as_subject)
        row.add_widget(self.as_deadline)
        add = Button(text="Add assignment", size_hint_y=None, height=dp(44))
        add.bind(on_release=lambda *a: self.add_assignment())
        for w in (self.as_title, row, add):
            root.add_widget(w)
        self.as_list = ScrollList()
        root.add_widget(self.as_list)
        tab.add_widget(root)
        self.add_widget(tab)

    def add_assignment(self):
        try:
            core.add_assignment(self.as_title.text, self.as_subject.text, self.as_deadline.text)
        except ValueError as exc:
            show_message("Invalid input", str(exc))
            return
        self.as_title.text = ""
        self.as_subject.text = ""
        self.refresh_all()

    def refresh_assignments(self):
        self.as_list.clear()
        today = date.today()
        for aid, title, subject, deadline, done in core.list_assignments():
            left = (core.parse_date(deadline) - today).days
            if done:
                status, color = "Done", (0.6, 0.6, 0.6, 1)
            elif left < 0:
                status, color = "Overdue", (1, 0.4, 0.4, 1)
            elif left == 0:
                status, color = "Due today", (1, 0.8, 0.3, 1)
            else:
                status, color = f"{left} day(s) left", (1, 1, 1, 1)
            row = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(4))
            sub = f" ({subject})" if subject else ""
            lbl = Label(text=f"{title}{sub}\n[size=13sp]{deadline}  -  {status}[/size]",
                        markup=True, halign="left", valign="middle", color=color)
            lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
            toggle = Button(text="Undo" if done else "Done", size_hint_x=None, width=dp(64))
            toggle.bind(on_release=lambda _b, a=aid: self.toggle(a))
            delete = Button(text="Del", size_hint_x=None, width=dp(56))
            delete.bind(on_release=lambda _b, a=aid: self.delete_assignment(a))
            for w in (lbl, toggle, delete):
                row.add_widget(w)
            self.as_list.add_row(row)

    def toggle(self, assignment_id):
        core.toggle_done(assignment_id)
        self.refresh_all()

    def delete_assignment(self, assignment_id):
        core.delete_assignment(assignment_id)
        self.refresh_all()

    # ---------------- misc ----------------
    def refresh_all(self):
        self.refresh_timetable()
        self.refresh_assignments()
        self.refresh_bag()


class PlannerApp(App):
    title = "Student Planner"

    def build(self):
        core.set_db_file(notify.db_path())
        core.init_db()
        self.root_widget = PlannerRoot()
        return self.root_widget

    def on_start(self):
        notify.request_notification_permission()
        if notify.on_android():
            notify.start_reminder_service()  # the service sends the 7 PM reminder
        else:
            Clock.schedule_interval(self.desktop_reminder_check, 60)  # desktop testing only

    def on_resume(self):
        self.root_widget.refresh_all()  # new day -> refresh "today"
        return True

    def desktop_reminder_check(self, _dt):
        if core.reminder_due():
            core.mark_reminder_sent()
            self.root_widget.send_test_reminder()


if __name__ == "__main__":
    PlannerApp().run()
