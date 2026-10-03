import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import {
    assertSteps,
    click,
    contains,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { test } from "@odoo/hoot";
import { advanceTime, mockDate } from "@odoo/hoot-mock";
import {
    onRpc,
    patchWithCleanup,
    preloadBundle,
    serverState,
} from "@web/../tests/web_test_helpers";

defineCalendarModels();
preloadBundle("web.fullcalendar_lib");

test("can listen on bus and display notifications in DOM and click OK", async () => {
    const pyEnv = await startServer();
    onRpc("/calendar/notify_ack", () => step("notifyAck"));
    await start();
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "calendar.alarm", [
        {
            alarm_id: 1,
            event_id: 2,
            title: "Meeting",
            message: "Very old meeting message",
            timer: 0,
            notify_at: "1978-04-14 12:45:00",
        },
    ]);
    await contains(".o_notification", { text: "Very old meeting message" });
    await click(".o_notification_buttons button", { text: "OK" });
    await contains(".o_notification", { count: 0 });
    assertSteps(["notifyAck"]);
});

test("can listen on bus and display notifications in DOM and click Detail", async () => {
    const pyEnv = await startServer();
    const env = await start();
    patchWithCleanup(env.services.action, {
        doAction(actionId) {
            step(actionId.type);
        },
    });
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "calendar.alarm", [
        {
            alarm_id: 1,
            event_id: 2,
            title: "Meeting",
            message: "Very old meeting message",
            timer: 0,
            notify_at: "1978-04-14 12:45:00",
        },
    ]);
    await contains(".o_notification", { text: "Very old meeting message" });
    await click(".o_notification_buttons button", { text: "Details" });
    await contains(".o_notification", { count: 0 });
    assertSteps(["ir.actions.act_window"]);
});

test("fetches the pending alarms on startup, without waiting for a bus notification", async () => {
    await startServer();
    onRpc("/calendar/notify", () => {
        step("notify");
        return [
            {
                alarm_id: 1,
                event_id: 2,
                title: "Meeting",
                message: "Meeting saved in a previous session",
                timer: 0,
                notify_at: "1978-04-14 12:45:00",
            },
        ];
    });
    await start();
    await contains(".o_notification", { text: "Meeting saved in a previous session" });
    assertSteps(["notify"]);
});

test("schedules the alarm from notify_at rather than from the stale timer", async () => {
    mockDate("2024-10-20 10:00:00");
    const pyEnv = await startServer();
    await start();
    // 'timer' is computed when the alarm is pushed: a payload replayed by the
    // bus after a reload carries a value that already elapsed.
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "calendar.alarm", [
        {
            alarm_id: 1,
            event_id: 2,
            title: "Meeting",
            message: "Meeting in five minutes",
            timer: 0,
            notify_at: "2024-10-20 10:05:00",
        },
    ]);
    await contains(".o_notification", { count: 0 });
    await advanceTime(5 * 60 * 1000);
    await contains(".o_notification", { text: "Meeting in five minutes" });
});

test("can listen on bus and display notifications in DOM and click Snooze", async () => {
    const pyEnv = await startServer();
    onRpc("/calendar/notify_ack", () => step("notifyAck"));
    await start();
    pyEnv["bus.bus"]._sendone(serverState.partnerId, "calendar.alarm", [
        {
            alarm_id: 1,
            event_id: 2,
            title: "Meeting",
            message: "Very old meeting message",
            timer: 0,
            notify_at: "1978-04-14 12:45:00",
        },
    ]);
    await contains(".o_notification", { text: "Very old meeting message" });
    await click(".o_notification button", { text: "Snooze" });
    await contains(".o_notification", { count: 0 });
    assertSteps([]);
});
