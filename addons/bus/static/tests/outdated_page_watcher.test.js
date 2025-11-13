import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { describe, expect, test } from "@odoo/hoot";
import { runAllTimers, waitFor } from "@odoo/hoot-dom";
import {
    contains,
    getService,
    MockServer,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { WebClient } from "@web/webclient/webclient";
import { addBusServiceListeners, defineBusModels, startBusService } from "./bus_test_helpers";

defineBusModels();
describe.current.tags("desktop");

test("disconnect during vacuum should ask for reload", async () => {
    browser.location.addEventListener("reload", () => expect.step("reload"));
    addBusServiceListeners(
        ["BUS:CONNECT", () => expect.step("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => expect.step("BUS:DISCONNECT")],
        ["BUS:RECONNECTING", () => expect.step("BUS:RECONNECTING")],
        ["BUS:RECONNECT", () => expect.step("BUS:RECONNECT")]
    );
    onRpc("/bus/has_missed_notifications", () => true);
    await mountWithCleanup(WebClient);
    browser.localStorage.setItem("bus.last_notification_id", 1);
    startBusService();
    expect(await getService("multi_tab").isOnMainTab()).toBe(true);
    await runAllTimers();
    await expect.waitForSteps(["BUS:CONNECT"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await expect.waitForSteps(["BUS:DISCONNECT", "BUS:RECONNECTING"]);
    await runAllTimers();
    await expect.waitForSteps(["BUS:RECONNECT"]);
    await waitFor(".o_notification");
    expect(".o_notification_content:first").toHaveText(
        "The page is out of date. Save your work and refresh to get the latest updates and avoid potential issues."
    );
    await contains(".o_notification button:contains(Refresh)").click();
    await expect.waitForSteps(["reload"]);
});

test("reconnect after going offline after bus gc should ask for reload", async () => {
    addBusServiceListeners(
        ["BUS:CONNECT", () => expect.step("BUS:CONNECT")],
        ["BUS:DISCONNECT", () => expect.step("BUS:DISCONNECT")]
    );
    onRpc("/bus/has_missed_notifications", () => true);
    await mountWithCleanup(WebClient);
    browser.localStorage.setItem("bus.last_notification_id", 1);
    startBusService();
    expect(await getService("multi_tab").isOnMainTab()).toBe(true);
    await runAllTimers();
    await expect.waitForSteps(["BUS:CONNECT"]);
    browser.dispatchEvent(new Event("offline"));
    await expect.waitForSteps(["BUS:DISCONNECT"]);
    browser.dispatchEvent(new Event("online"));
    await runAllTimers();
    await expect.waitForSteps(["BUS:CONNECT"]);
    await waitFor(".o_notification");
    expect(".o_notification_content:first").toHaveText(
        "The page is out of date. Save your work and refresh to get the latest updates and avoid potential issues."
    );
});
