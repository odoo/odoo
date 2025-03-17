import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { describe, expect, test } from "@odoo/hoot";
import { runAllTimers, waitFor } from "@odoo/hoot-dom";
import {
    asyncStep,
    contains,
    MockServer,
    mountWithCleanup,
    onRpc,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { serializeDateTime } from "@web/core/l10n/dates";
import { WebClient } from "@web/webclient/webclient";
import { addBusServiceListeners, defineBusModels, startBusService } from "./bus_test_helpers";

defineBusModels();
describe.current.tags("desktop");

const { DateTime } = luxon;
test("disconnect during vacuum should ask for reload", async () => {
    browser.location.addEventListener("reload", () => asyncStep("reload"));
    addBusServiceListeners(
        ["connect", () => asyncStep("connect")],
        ["disconnect", () => (lastDisconnectDt = DateTime.now())]
    );
    // Vacuum permanently clears notifs, so reload might be required to recover
    // coherent state in apps like Discuss.
    let lastDisconnectDt;
    onRpc("/bus/get_autovacuum_info", () => ({
        lastcall: serializeDateTime(lastDisconnectDt.plus({ minute: 1 })),
        nextcall: serializeDateTime(DateTime.now().plus({ day: 1 })),
    }));
    await mountWithCleanup(WebClient);
    startBusService();
    await runAllTimers();
    await waitForSteps(["connect"]);
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await runAllTimers();
    await waitFor(".o_notification");
    expect(".o_notification_content:first").toHaveText(
        "Save your work and refresh to get the latest updates and avoid potential issues."
    );
    await contains(".o_notification button:contains(Refresh)").click();
    await waitForSteps(["reload"]);
});
