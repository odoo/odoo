import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { describe, expect, test } from "@odoo/hoot";
import { queryFirst, waitFor } from "@odoo/hoot-dom";
import {
    asyncStep,
    contains,
    MockServer,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { serializeDateTime } from "@web/core/l10n/dates";
import { WebClient } from "@web/webclient/webclient";
import { defineBusModels } from "./bus_test_helpers";

defineBusModels();
describe.current.tags("desktop");

const { DateTime } = luxon;
test("disconnect during vacuum should ask for reload", async () => {
    // Vacuum permanently clears notifs, so reload might be required to recover
    // coherent state in apps like Discuss.
    let lastDisconnectDt;
    patchWithCleanup(browser.location, { reload: () => asyncStep("reload") });
    onRpc("/bus/get_autovacuum_info", () => ({
        lastcall: serializeDateTime(lastDisconnectDt.plus({ minute: 1 })),
        nextcall: serializeDateTime(DateTime.now().plus({ day: 1 })),
    }));
    const { env } = await mountWithCleanup(WebClient);
    env.services.bus_service.addEventListener(
        "disconnect",
        () => (lastDisconnectDt = DateTime.now())
    );
    env.services.bus_service.addEventListener("connect", () => asyncStep("connect"));
    env.services.bus_service.start();
    await waitForSteps(["connect"]);
    MockServer.current.env["bus.bus"]._simulateDisconnection(
        WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE
    );
    await waitFor(".o_notification");
    expect(queryFirst(".o_notification_content")).toHaveText(
        "Save your work and refresh to get the latest updates and avoid potential issues."
    );
    await contains(".o_notification button:contains(Refresh)").click();
    await waitForSteps(["reload"]);
});
