import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import { click, contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { test } from "@odoo/hoot";
import {
    asyncStep,
    mockService,
    onRpc,
    preloadBundle,
    serverState,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

defineCalendarModels();
preloadBundle("web.fullcalendar_lib");

test("can listen on bus and display notifications in DOM and click OK", async () => {
    const pyEnv = await startServer();
    onRpc("/calendar/notify_ack", () => asyncStep("notify_ack"));
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
    await contains(".o_notification", { text: "Meeting. Very old meeting message" });
    await click(".o_notification_buttons button", { text: "OK" });
    await contains(".o_notification", { count: 0 });
    await waitForSteps(["notify_ack"]);
});

test("can listen on bus and display notifications in DOM and click Detail", async () => {
    mockService("action", {
        doAction(actionId) {
            asyncStep(actionId.type);
        },
    });
    const pyEnv = await startServer();
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
    await contains(".o_notification", { text: "Meeting. Very old meeting message" });
    await click(".o_notification_buttons button", { text: "Details" });
    await contains(".o_notification", { count: 0 });
    await waitForSteps(["ir.actions.act_window"]);
});

test("can listen on bus and display notifications in DOM and click Snooze", async () => {
    const pyEnv = await startServer();
    onRpc("/calendar/notify_ack", () => asyncStep("notify_ack"));
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
    await contains(".o_notification", { text: "Meeting. Very old meeting message" });
    await click(".o_notification button", { text: "Snooze" });
    await contains(".o_notification", { count: 0 });
    await waitForSteps([]);
});
