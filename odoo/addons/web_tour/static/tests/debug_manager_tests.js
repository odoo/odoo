/** @odoo-module **/

import { disableTours } from "@web_tour/debug/debug_manager";

import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { browser } from "@web/core/browser/browser";

import { click, getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService, fakeCommandService } from "@web/../tests/helpers/mock_services";
import { DebugMenuParent } from "@web/../tests/core/debug/debug_manager_tests";

const debugRegistry = registry.category("debug");
let target;

QUnit.module("Tours", (hooks) => {

    QUnit.module("DebugManager");

    hooks.beforeEach(async () => {
        target = getFixture();
        registry
            .category("services")
            .add("hotkey", hotkeyService)
            .add("ui", uiService)
            .add("orm", ormService)
            .add("localization", makeFakeLocalizationService())
            .add("command", fakeCommandService);
    });

    QUnit.test("can disable tours", async (assert) => {
        debugRegistry.category("default").add("disableTours", disableTours);

        const fakeLocalStorage = {
            tour__sampletour1__currentIndex: "0",
            tour__sampletour1__stepDelay: "0",
            tour__sampletour1__keepWatchBrowser: "0",
            tour__sampletour1__showPointerDuration: "0",
            tour__sampletour1__mode: "manual",
            tour__sampletour2__currentIndex: "0",
            tour__sampletour2__stepDelay: "0",
            tour__sampletour2__keepWatchBrowser: "0",
            tour__sampletour2__showPointerDuration: "0",
            tour__sampletour2__mode: "manual",
        };

        Object.defineProperties(fakeLocalStorage, {
            getItem: {
                value(key) {
                    return fakeLocalStorage[key];
                },
                enumerable: false,
            },
            removeItem: {
                value(key) {
                    delete fakeLocalStorage[key];
                },
                enumerable: false,
            },
        });

        patchWithCleanup(browser, { localStorage: fakeLocalStorage });

        const mockRPC = async (_route, args) => {
            if (args.method === "check_access_rights") {
                return Promise.resolve(true);
            }
            if (args.method === "consume") {
                assert.step("consume");
                assert.deepEqual(args.args[0], ["sampletour1", "sampletour2"]);
                return Promise.resolve(true);
            }
        };
        const env = await makeTestEnv({ mockRPC });

        await mount(DebugMenuParent, target, { env });

        await click(target.querySelector("button.dropdown-toggle"));

        assert.containsOnce(target, ".dropdown-item");
        await click(target.querySelector(".dropdown-item"));
        assert.verifySteps(["consume"]);
    });
});
