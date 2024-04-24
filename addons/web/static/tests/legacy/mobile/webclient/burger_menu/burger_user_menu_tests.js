/** @odoo-module alias=@web/../tests/mobile/webclient/burger_menu/burger_user_menu_tests default=false */

import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { BurgerUserMenu } from "@web/webclient/burger_menu/burger_user_menu/burger_user_menu";
import { preferencesItem } from "@web/webclient/user_menu/user_menu_items";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { click, getFixture, mount } from "@web/../tests/helpers/utils";

const serviceRegistry = registry.category("services");
const userMenuRegistry = registry.category("user_menuitems");
let target;
let env;

QUnit.module("BurgerUserMenu", {
    async beforeEach() {
        serviceRegistry.add("hotkey", hotkeyService);
        target = getFixture();
    },
});

QUnit.test("can be rendered", async (assert) => {
    env = await makeTestEnv();
    userMenuRegistry.add("bad_item", function () {
        return {
            type: "item",
            id: "bad",
            description: "Bad",
            callback: () => {
                assert.step("callback bad_item");
            },
            sequence: 10,
        };
    });
    userMenuRegistry.add("ring_item", function () {
        return {
            type: "item",
            id: "ring",
            description: "Ring",
            callback: () => {
                assert.step("callback ring_item");
            },
            sequence: 5,
        };
    });
    userMenuRegistry.add("frodo_item", function () {
        return {
            type: "switch",
            id: "frodo",
            description: "Frodo",
            callback: () => {
                assert.step("callback frodo_item");
            },
            sequence: 11,
        };
    });
    userMenuRegistry.add("separator", function () {
        return {
            type: "separator",
            sequence: 15,
        };
    });
    userMenuRegistry.add("invisible_item", function () {
        return {
            type: "item",
            id: "hidden",
            description: "Hidden Power",
            callback: () => {
                assert.step("callback hidden_item");
            },
            sequence: 5,
            hide: true,
        };
    });
    userMenuRegistry.add("eye_item", function () {
        return {
            type: "item",
            id: "eye",
            description: "Eye",
            callback: () => {
                assert.step("callback eye_item");
            },
        };
    });
    await mount(BurgerUserMenu, target, { env });
    assert.containsN(target, "a", 3);
    assert.containsOnce(target, ".form-switch input.form-check-input");
    assert.containsOnce(target, "hr");
    const items = [...target.querySelectorAll("a, .form-switch")] || [];
    assert.deepEqual(
        items.map((el) => el.textContent),
        ["Ring", "Bad", "Frodo", "Eye"]
    );
    for (const item of items) {
        click(item);
    }
    assert.verifySteps([
        "callback ring_item",
        "callback bad_item",
        "callback frodo_item",
        "callback eye_item",
    ]);
});

QUnit.test("can execute the callback of settings", async (assert) => {
    const mockRPC = (route) => {
        if (route === "/web/dataset/call_kw/res.users/action_get") {
            return Promise.resolve({
                name: "Change My Preferences",
                res_id: 0,
            });
        }
    };
    const testConfig = { mockRPC };
    serviceRegistry.add("localization", makeFakeLocalizationService());
    serviceRegistry.add("orm", ormService);
    const fakeActionService = {
        name: "action",
        start() {
            return {
                doAction(actionId) {
                    assert.step("" + actionId.res_id);
                    assert.step(actionId.name);
                    return Promise.resolve(true);
                },
            };
        },
    };
    serviceRegistry.add("action", fakeActionService, { force: true });

    env = await makeTestEnv(testConfig);
    userMenuRegistry.add("profile", preferencesItem);
    await mount(BurgerUserMenu, target, { env });
    assert.containsOnce(target, "a");
    const item = target.querySelector("a");
    assert.strictEqual(item.textContent, "Preferences");
    await click(item);
    assert.verifySteps(["7", "Change My Preferences"]);
});
