/** @odoo-module alias=@bus/../tests/assets_watchdog_tests default=false */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addBusServicesToRegistry } from "@bus/../tests/helpers/test_utils";
import { waitForBusEvent } from "@bus/../tests/helpers/websocket_event_deferred";
import { outdatedPageWatcherService } from "@bus/outdated_page_watcher_service";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { patchWithCleanup } from "@web/../tests/legacy/helpers/utils";
import { assertSteps, click, contains, step } from "@web/../tests/legacy/utils";
import { createWebClient } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";

const { DateTime } = luxon;
QUnit.test("disconnect during vacuum should ask for reload", async () => {
    // vacuum permanently clears notifs, so reload might be required to recover coherent state in apps like Discuss
    addBusServicesToRegistry();
    registry.category("services").add("bus.outdated_page_watcher", outdatedPageWatcherService);
    const pyEnv = await startServer();
    const { env } = await createWebClient({
        mockRPC(route) {
            if (route === "/bus/get_autovacuum_info") {
                return {
                    lastcall: serializeDateTime(lastDisconnectDt.plus({ minute: 1 })),
                    nextcall: serializeDateTime(DateTime.now().plus({ day: 1 })),
                };
            }
        },
    });
    let lastDisconnectDt;
    env.services.bus_service.addEventListener(
        "disconnect",
        () => (lastDisconnectDt = DateTime.now())
    );
    env.services.bus_service.start();
    await waitForBusEvent(env, "connect");
    pyEnv.simulateConnectionLost(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await contains(".o_notification", {
        text: "Save your work and refresh to get the latest updates and avoid potential issues.",
    });
    patchWithCleanup(browser.location, { reload: () => step("reload") });
    await click(".o_notification button", { text: "Refresh" });
    await assertSteps(["reload"]);
});
