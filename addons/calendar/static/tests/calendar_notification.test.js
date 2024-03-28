import { test } from "@odoo/hoot";
import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { onRpc, serverState } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

defineMailModels();
defineCalendarModels();

test("can listen on bus and display notifications in DOM and click OK", async () => {
    const pyEnv = await startServer();
    onRpc("/calendar/notify_ack", () => {
        step("notifyAck");
    });
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
    const fakeActionService = {
        name: "action",
        start() {
            return {
                doAction(actionId) {
                    step(actionId.type);
                    return Promise.resolve(true);
                },
                loadState(state, options) {
                    return Promise.resolve(true);
                },
            };
        },
    };
    registry.category("services").add("action", fakeActionService, { force: true });
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
    await click(".o_notification_buttons button", { text: "Details" });
    await contains(".o_notification", { count: 0 });
    assertSteps(["ir.actions.act_window"]);
});

test("can listen on bus and display notifications in DOM and click Snooze", async () => {
    const pyEnv = await startServer();
    onRpc("/calendar/notify_ack", () => {
        step("notifyAck");
    });
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
    assertSteps([], "should only close the notification withtout calling a rpc");
});
