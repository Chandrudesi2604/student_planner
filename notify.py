"""Notifications + shared helpers for Android (and a safe fallback on desktop)."""
import os


def on_android():
    return "ANDROID_ARGUMENT" in os.environ or "ANDROID_PRIVATE" in os.environ


def db_path():
    """Same database file for the app and the background service."""
    if on_android():
        base = os.environ.get("ANDROID_PRIVATE") or os.environ.get("ANDROID_ARGUMENT", ".")
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "planner.db")


def _android_context():
    from jnius import autoclass

    try:  # inside the background service
        ctx = autoclass("org.kivy.android.PythonService").mService
        if ctx is not None:
            return ctx
    except Exception:
        pass
    return autoclass("org.kivy.android.PythonActivity").mActivity


def send_notification(title, message, notif_id=1):
    """Show a system notification. Returns True if it was handed to Android."""
    if not on_android():
        print(f"[notification] {title}\n{message}")
        return False
    try:
        from jnius import autoclass

        ctx = _android_context()
        Build_VERSION = autoclass("android.os.Build$VERSION")
        Context = autoclass("android.content.Context")
        NotificationBuilder = autoclass("android.app.Notification$Builder")
        BigText = autoclass("android.app.Notification$BigTextStyle")
        manager = ctx.getSystemService(Context.NOTIFICATION_SERVICE)
        channel_id = "planner_reminders"

        builder = None
        if Build_VERSION.SDK_INT >= 26:
            NotificationChannel = autoclass("android.app.NotificationChannel")
            channel = NotificationChannel(channel_id, "Planner reminders", 4)  # IMPORTANCE_HIGH
            manager.createNotificationChannel(channel)
            builder = NotificationBuilder(ctx, channel_id)
        else:
            builder = NotificationBuilder(ctx)

        icon = ctx.getApplicationInfo().icon
        builder.setSmallIcon(icon)
        builder.setContentTitle(title)
        builder.setContentText(message.split("\n")[0])
        builder.setStyle(BigText().bigText(message))
        builder.setAutoCancel(True)

        # tapping the notification opens the app
        PendingIntent = autoclass("android.app.PendingIntent")
        Intent = autoclass("android.content.Intent")
        pkg = ctx.getPackageManager().getLaunchIntentForPackage(ctx.getPackageName())
        if pkg is not None:
            flags = PendingIntent.FLAG_UPDATE_CURRENT
            if Build_VERSION.SDK_INT >= 23:
                flags |= PendingIntent.FLAG_IMMUTABLE
            builder.setContentIntent(PendingIntent.getActivity(ctx, 0, pkg, flags))

        manager.notify(notif_id, builder.build())
        return True
    except Exception as exc:  # never crash the app/service over a notification
        print("notification failed:", exc)
        return False


def request_notification_permission():
    """Android 13+ needs a runtime permission to show notifications."""
    if not on_android():
        return
    try:
        from android.permissions import Permission, request_permissions

        request_permissions([Permission.POST_NOTIFICATIONS])
    except Exception as exc:
        print("permission request failed:", exc)


def start_reminder_service():
    """Start the background service that fires the 7 PM reminder."""
    if not on_android():
        return
    try:
        from jnius import autoclass

        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        pkg = activity.getPackageName()
        service = autoclass(pkg + ".ServiceReminder")
        service.start(activity, "")
    except Exception as exc:
        print("could not start service:", exc)
