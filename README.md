# Student Planner (Kivy / Android)

Timetable + "Pack Bag" checklist + assignments, with a 7:00 PM reminder for tomorrow.

## Files
- `main.py` - Kivy screens (Pack Bag, Timetable, Assignments)
- `core.py` - database + logic (same as the desktop version)
- `notify.py` - Android notifications, permission request, service start
- `service.py` - background service that sends the 7 PM reminder
- `buildozer.spec` - Android build settings

## Try it on a computer first
```
pip install kivy
python main.py
```
(On desktop the reminder is shown as a pop-up; "Send test reminder now" works anywhere.)

## Build the APK (Linux, WSL, or Google Colab)
```
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config \
    zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
pip install --user buildozer cython
buildozer android debug
```
The first build takes 20-40 minutes. The APK appears in `bin/`. Copy it to your
phone and install it (allow "install from unknown sources").

## Make the reminder reliable on your phone
1. Open the app once and **Allow** notifications.
2. Settings > Apps > Student Planner > Battery > set to **Unrestricted / Don't optimise**
   (many phones - Xiaomi, Oppo, Vivo, Samsung - kill background services otherwise).
3. Use "Send test reminder now" to confirm notifications show up.

If the phone was restarted, open the app once to start the reminder service again.
