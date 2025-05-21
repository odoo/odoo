import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { describe, expect, test } from "@odoo/hoot";
import { runAllTimers, waitFor } from "@odoo/hoot-dom";
import {
    asyncStep,
    contains,
    getService,
    MockServer,
    mountWithCleanup,
    onRpc,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { WebClient } from "@web/webclient/webclient";
import { addBusServiceListeners, defineBusModels, startBusService } from "./bus_test_helpers";

defineBusModels();
describe.current.tags("desktop");

test("disconnect during vacuum should ask for reload", async () => {
    browser.location.addEventListener("reload", () => asyncStep("reload"));
    addBusServiceListeners(
        ["connect", () => asyncStep("connect")],
        ["disconnect", () => asyncStep("disconnect")],
        ["reconnecting", () => asyncStep("reconnecting")],
        ["reconnect", () => asyncStep("reconnect")]
    );
    onRpc("/bus/has_missed_notifications", () => true);
    await mountWithCleanup(WebClient);
    getService("multi_tab").setSharedValue("last_notification_id", 1);
    startBusService();
    await runAllTimers();
    await waitForSteps(["connect"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForSteps(["disconnect", "reconnecting"]);
    await runAllTimers();
    await waitForSteps(["reconnect"]);
    await waitFor(".o_notification");
    expect(".o_notification_content:first").toHaveText(
        "Save your work and refresh to get the latest updates and avoid potential issues."
    );
    await contains(".o_notification button:contains(Refresh)").click();
    await waitForSteps(["reload"]);
});

test("reconnect after going offline after bus gc should ask for reload", async () => {
    addBusServiceListeners(
        ["connect", () => asyncStep("connect")],
        ["disconnect", () => asyncStep("disconnect")]
    );
    onRpc("/bus/has_missed_notifications", () => true);
    await mountWithCleanup(WebClient);
    getService("multi_tab").setSharedValue("last_notification_id", 1);
    startBusService();
    await runAllTimers();
    await waitForSteps(["connect"]);
    browser.dispatchEvent(new Event("offline"));
    await waitForSteps(["disconnect"]);
    browser.dispatchEvent(new Event("online"));
    await runAllTimers();
    await waitForSteps(["connect"]);
    await waitFor(".o_notification");
    expect(".o_notification_content:first").toHaveText(
        "Save your work and refresh to get the latest updates and avoid potential issues."
    );
});
