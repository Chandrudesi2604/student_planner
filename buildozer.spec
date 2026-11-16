[app]
title = Student Planner
package.name = studentplanner
package.domain = org.studentplanner
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy,pyjnius,android,sqlite3

orientation = portrait
fullscreen = 0

# Background service that sends the 7 PM reminder (runs as a foreground service)
services = Reminder:service.py:foreground

android.permissions = POST_NOTIFICATIONS,FOREGROUND_SERVICE,WAKE_LOCK
# API 33 on purpose: API 34+ requires a declared foreground-service type,
# which the default Buildozer service template does not set.
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
