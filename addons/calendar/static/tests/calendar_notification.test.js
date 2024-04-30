import { test } from "@odoo/hoot";
import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import {
    assertSteps,
    click,
    contains,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { onRpc, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

defineCalendarModels();

test("can listen on bus and display notifications in DOM and click OK", async () => {
    const pyEnv = await startServer();
    onRpc("/calendar/notify_ack", () => { step("notifyAck") });
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

test("can listen on bus and display notifications in DOM and click Snooze", async () => {
    const pyEnv = await startServer();
    onRpc("/calendar/notify_ack", () => { step("notifyAck") });
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
