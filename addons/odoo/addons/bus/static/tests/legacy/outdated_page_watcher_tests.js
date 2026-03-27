/** @odoo-module alias=@bus/../tests/assets_watchdog_tests default=false */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addBusServicesToRegistry } from "@bus/../tests/helpers/test_utils";
import { waitForBusEvent } from "@bus/../tests/helpers/websocket_event_deferred";
import { outdatedPageWatcherService } from "@bus/outdated_page_watcher_service";
import { BACK_ONLINE_RECONNECT_DELAY } from "@bus/services/bus_service";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import { mockTimeout, patchWithCleanup } from "@web/../tests/legacy/helpers/utils";
import { assertSteps, click, contains, step } from "@web/../tests/legacy/utils";
import { createWebClient } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

QUnit.test("disconnect during bus gc should ask for reload", async () => {
    // When the bus table is cleared, reload might be required to recover
    // coherent state in apps like Discuss.
    addBusServicesToRegistry();
    registry.category("services").add("bus.outdated_page_watcher", outdatedPageWatcherService);
    const pyEnv = await startServer();
    const { env } = await createWebClient({
        mockRPC(route) {
            if (route === "/bus/has_missed_notifications") {
                return true;
            }
        },
    });
    env.services.multi_tab.setSharedValue("last_notification_id", 1);
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

QUnit.test("reconnect after going offline after bus gc should ask for reload", async () => {
    addBusServicesToRegistry();
    registry.category("services").add("bus.outdated_page_watcher", outdatedPageWatcherService);
    const { advanceTime } = mockTimeout();
    const { env } = await createWebClient({
        mockRPC(route) {
            if (route === "/bus/has_missed_notifications") {
                return true;
            }
        },
    });
    env.services.multi_tab.setSharedValue("last_notification_id", 1);
    env.services.bus_service.start();
    await waitForBusEvent(env, "connect");
    browser.dispatchEvent(new Event("offline"));
    await waitForBusEvent(env, "disconnect");
    browser.dispatchEvent(new Event("online"));
    await advanceTime(BACK_ONLINE_RECONNECT_DELAY);
    await contains(".o_notification", {
        text: "Save your work and refresh to get the latest updates and avoid potential issues.",
    });
});
