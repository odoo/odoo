/** @odoo-module */

import { busService } from "@bus/services/bus_service";
import { presenceService } from "@bus/services/presence_service";
import { multiTabService } from "@bus/multi_tab_service";
import { getPyEnv } from '@bus/../tests/helpers/mock_python_environment';

import { createWebClient } from "@web/../tests/webclient/helpers";
import { assetsWatchdogService } from "@bus/services/assets_watchdog_service";
import { click, getFixture, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

QUnit.module("Bus Assets WatchDog", (hooks) => {
    let target;
    hooks.beforeEach((assert) => {
        serviceRegistry.add("assetsWatchdog", assetsWatchdogService);
        serviceRegistry.add("bus_service", busService);
        serviceRegistry.add("presence", presenceService);
        serviceRegistry.add("multi_tab", multiTabService);
        patchWithCleanup(browser, {
            setTimeout(fn) {
                return this._super(fn, 0);
            },
            location: {
                reload: () => assert.step("reloadPage"),
            },
        });

        target = getFixture();
    });

    QUnit.test("can listen on bus and displays notifications in DOM", async (assert) => {
        assert.expect(4);

        await createWebClient({});
        const pyEnv = await getPyEnv();
        pyEnv['bus.bus']._sendone("broadcast", "bundle_changed", {
            server_version: "NEW_MAJOR_VERSION"
        });

        await nextTick();

        assert.containsOnce(target, ".o_notification_body");
        assert.strictEqual(
            target.querySelector(".o_notification_body .o_notification_content").textContent,
            "The page appears to be out of date."
        );

        // reload by clicking on the reload button
        await click(target, ".o_notification_buttons .btn-primary");
        assert.verifySteps(["reloadPage"]);
    });
});
