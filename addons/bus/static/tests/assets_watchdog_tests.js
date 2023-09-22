/* @odoo-module */

import { busService } from "@bus/services/bus_service";
import { busParametersService } from "@bus/bus_parameters_service";
import { presenceService } from "@bus/services/presence_service";
import { multiTabService } from "@bus/multi_tab_service";
import { getPyEnv } from "@bus/../tests/helpers/mock_python_environment";

import { assetsWatchdogService } from "@bus/services/assets_watchdog_service";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { createWebClient } from "@web/../tests/webclient/helpers";
import { click, contains } from "@web/../tests/utils";

const serviceRegistry = registry.category("services");

QUnit.module("Bus Assets WatchDog", (hooks) => {
    hooks.beforeEach((assert) => {
        serviceRegistry.add("assetsWatchdog", assetsWatchdogService);
        serviceRegistry.add("bus_service", busService);
        serviceRegistry.add("bus.parameters", busParametersService);
        serviceRegistry.add("presence", presenceService);
        serviceRegistry.add("multi_tab", multiTabService);
        patchWithCleanup(browser, {
            setTimeout(fn) {
                return super.setTimeout(fn, 0);
            },
            location: {
                reload: () => assert.step("reloadPage"),
            },
        });
    });

    QUnit.test("can listen on bus and displays notifications in DOM", async (assert) => {
        await createWebClient({});
        const pyEnv = await getPyEnv();
        pyEnv["bus.bus"]._sendone("broadcast", "bundle_changed", {
            server_version: "NEW_MAJOR_VERSION",
        });
        await contains(".o_notification", { text: "The page appears to be out of date." });
        await click(".o_notification_buttons .btn-primary", { text: "Refresh" });
        assert.verifySteps(["reloadPage"]);
    });
});
