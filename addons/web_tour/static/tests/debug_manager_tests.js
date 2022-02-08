/** @odoo-module **/

import { disableTours } from "@web_tour/debug/debug_manager";

import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";

import { click, getFixture } from "@web/../tests/helpers/utils";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { DebugMenuParent } from "@web/../tests/core/debug/debug_manager_tests";
import { fakeCommandService } from "@web/../tests/helpers/mock_services";

const { mount } = owl;

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

        const fakeTourService = {
            start(env) {
                return {
                    getActiveTours() {
                        return [{ name: 'a' }, { name: 'b' }];
                    }
                }
            },
        };
        registry.category("services").add("tour", fakeTourService);

        const mockRPC = async (route, args) => {
            if (args.method === "check_access_rights") {
                return Promise.resolve(true);
            }
            if (args.method === "consume") {
                assert.step("consume");
                assert.deepEqual(args.args[0], ['a', 'b']);
                return Promise.resolve(true);
            }
        };
        const env = await makeTestEnv({ mockRPC });

        const debugManager = await mount(DebugMenuParent, { env, target });
        registerCleanup(() => debugManager.destroy());

        await click(debugManager.el.querySelector("button.dropdown-toggle"));

        assert.containsOnce(debugManager.el, ".dropdown-item");
        await click(debugManager.el.querySelector(".dropdown-item"));
        assert.verifySteps(["consume"]);
    });
});
