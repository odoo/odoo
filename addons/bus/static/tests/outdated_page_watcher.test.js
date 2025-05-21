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
        ["BUS:CONNECT", () => asyncStep("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")],
        ["BUS:RECONNECTING", () => asyncStep("BUS:RECONNECTING")],
        ["BUS:RECONNECT", () => asyncStep("BUS:RECONNECT")]
    );
    onRpc("/bus/has_missed_notifications", () => true);
    await mountWithCleanup(WebClient);
    getService("legacy_multi_tab").setSharedValue("last_notification_id", 1);
    startBusService();
    expect(await getService("multi_tab").isOnMainTab()).toBe(true);
    await runAllTimers();
    await waitForSteps(["BUS:CONNECT"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await waitForSteps(["BUS:DISCONNECT", "BUS:RECONNECTING"]);
    await runAllTimers();
    await waitForSteps(["BUS:RECONNECT"]);
    await waitFor(".o_notification");
    expect(".o_notification_content:first").toHaveText(
        "The page is out of date. Save your work and refresh to get the latest updates and avoid potential issues."
    );
    await contains(".o_notification button:contains(Refresh)").click();
    await waitForSteps(["reload"]);
});

test("reconnect after going offline after bus gc should ask for reload", async () => {
    addBusServiceListeners(
        ["BUS:CONNECT", () => asyncStep("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => asyncStep("BUS:DISCONNECT")]
    );
    onRpc("/bus/has_missed_notifications", () => true);
    await mountWithCleanup(WebClient);
    getService("legacy_multi_tab").setSharedValue("last_notification_id", 1);
    startBusService();
    expect(await getService("multi_tab").isOnMainTab()).toBe(true);
    await runAllTimers();
    await waitForSteps(["BUS:CONNECT"]);
    browser.dispatchEvent(new Event("offline"));
    await waitForSteps(["BUS:DISCONNECT"]);
    browser.dispatchEvent(new Event("online"));
    await runAllTimers();
    await waitForSteps(["BUS:CONNECT"]);
    await waitFor(".o_notification");
    expect(".o_notification_content:first").toHaveText(
        "The page is out of date. Save your work and refresh to get the latest updates and avoid potential issues."
    );
});
