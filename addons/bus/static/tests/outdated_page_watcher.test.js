import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { describe, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-dom";
import {
    asyncStep,
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

test("notify subscribers when bus disconnect during vacuum", async () => {
    addBusServiceListeners(["connect", () => asyncStep("connect")]);
    onRpc("/bus/has_missed_notifications", () => true);
    await mountWithCleanup(WebClient);
    getService("bus.outdated_page_watcher").subscribe(() => asyncStep("outdated_page"));
    startBusService();
    await runAllTimers();
    await waitForSteps(["connect"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await runAllTimers();
    // Two events during tests because local storage event is triggered for the page
    // that sets it while it's not the case in real-life.
    await waitForSteps(["outdated_page", "outdated_page"]);
});

test("notify subscribers when bus reconnects post-vacuum after going offline", async () => {
    addBusServiceListeners(
        ["connect", () => asyncStep("connect")],
        ["disconnect", () => asyncStep("disconnect")]
    );
    onRpc("/bus/has_missed_notifications", () => true);
    await mountWithCleanup(WebClient);
    getService("bus.outdated_page_watcher").subscribe(() => asyncStep("outdated_page"));
    startBusService();
    await runAllTimers();
    await waitForSteps(["connect"]);
    browser.dispatchEvent(new Event("offline"));
    await waitForSteps(["disconnect"]);
    browser.dispatchEvent(new Event("online"));
    await runAllTimers();
    await waitForSteps(["connect"]);
    // Two events during tests because local storage event is triggered for the page
    // that sets it while it's not the case in real-life.
    await waitForSteps(["outdated_page", "outdated_page"]);
});
