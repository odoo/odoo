import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { getService, mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import {WebClient} from "@web/webclient/webclient";

import "@calendar/core/web/schedule_meeting";

defineCalendarModels();

function mockNotification() {
    mockService("notification", {
        add(message, options) {
            expect.step(`notification: ${message} (${options.type})`);
            return () => {};
        },
    });
}

test("action_then_notify defaults to an info toast", async () => {
    mockNotification();
    registry.category("actions").add("test_next_action", () => {});
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        type: "ir.actions.client",
        tag: "calendar.action_then_notify",
        params: {
            next: { type: "ir.actions.client", tag: "test_next_action" },
            message: "Pick a date and time",
        },
    });

    expect.verifySteps(["notification: Pick a date and time (info)"]);
});


test("action_then_notify shows the toast once the next action is done", async () => {
    mockNotification();
    registry.category("actions").add("test_next_action", async () => {
        expect.step("next action: start");
        await animationFrame();
        expect.step("next action: done");
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        type: "ir.actions.client",
        tag: "calendar.action_then_notify",
        params: {
            next: { type: "ir.actions.client", tag: "test_next_action" },
            message: "Pick a date and time",
            type: "info",
        },
    });

    expect.verifySteps([
        "next action: start",
        "next action: done",
        "notification: Pick a date and time (info)",
    ]);
});

test("action_then_notify without next only shows the toast", async () => {
    mockNotification();
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        type: "ir.actions.client",
        tag: "calendar.action_then_notify",
        params: { message: "Pick a date and time" },
    });

    expect.verifySteps(["notification: Pick a date and time (info)"]);
});
