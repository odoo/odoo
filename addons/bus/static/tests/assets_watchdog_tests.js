/* @odoo-module */

import { getPyEnv } from "@bus/../tests/helpers/mock_python_environment";
import { addBusServicesToRegistry } from "@bus/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";
import { createWebClient } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";

QUnit.module("Bus Assets WatchDog");

QUnit.test("can listen on bus and displays notifications in DOM", async (assert) => {
    addBusServicesToRegistry();
    patchWithCleanup(browser, {
        setTimeout(fn) {
            return super.setTimeout(fn, 0);
        },
        location: {
            reload: () => assert.step("reloadPage"),
        },
    });
    await createWebClient({});
    const pyEnv = await getPyEnv();
    pyEnv["bus.bus"]._sendone("broadcast", "bundle_changed", {
        server_version: "NEW_MAJOR_VERSION",
    });
    await contains(".o_notification", { text: "The page appears to be out of date." });
    await click(".o_notification_buttons .btn-primary", { text: "Refresh" });
    assert.verifySteps(["reloadPage"]);
});
