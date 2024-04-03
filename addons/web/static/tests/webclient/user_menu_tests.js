/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { preferencesItem } from "@web/webclient/user_menu/user_menu_items";
import { userService } from "@web/core/user_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import { click, getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { session } from "@web/session";

const serviceRegistry = registry.category("services");
const userMenuRegistry = registry.category("user_menuitems");
let target;
let env;

QUnit.module("UserMenu", {
    async beforeEach() {
        patchWithCleanup(session, { name: "Sauron" });
        patchWithCleanup(browser, {
            location: {
                origin: "http://lordofthering",
            },
        });
        serviceRegistry.add("user", userService);
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
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
            callback: () => {},
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
    await mount(UserMenu, target, { env });
    assert.containsOnce(target, "img.o_user_avatar");
    assert.strictEqual(
        target.querySelector("img.o_user_avatar").dataset.src,
        "http://lordofthering/web/image?model=res.users&field=avatar_128&id=7"
    );
    assert.containsOnce(target, "span.oe_topbar_name");
    assert.strictEqual(target.querySelector(".oe_topbar_name").textContent, "Sauron");
    assert.containsNone(target, ".dropdown-menu .dropdown-item");
    await click(target.querySelector("button.dropdown-toggle"));
    assert.containsN(target, ".dropdown-menu .dropdown-item", 4);
    assert.containsOnce(target, ".dropdown-menu .dropdown-item input.form-check-input");
    assert.containsOnce(target, "div.dropdown-divider");
    const children = [...(target.querySelector(".dropdown-menu").children || [])];
    assert.deepEqual(
        children.map((el) => el.tagName),
        ["SPAN", "SPAN", "SPAN", "DIV", "SPAN"]
    );
    const items = [...target.querySelectorAll(".dropdown-menu .dropdown-item")] || [];
    assert.deepEqual(
        items.map((el) => el.dataset.menu),
        ["ring", "bad", "frodo", "eye"]
    );
    assert.deepEqual(
        items.map((el) => el.textContent),
        ["Ring", "Bad", "Frodo", "Eye"]
    );
    for (const item of items) {
        click(item);
    }
    assert.verifySteps(["callback ring_item", "callback bad_item", "callback frodo_item", "callback eye_item"]);
});

QUnit.test("display the correct name in debug mode", async (assert) => {
    patchWithCleanup(odoo, { debug: "1" });
    env = await makeTestEnv();
    await mount(UserMenu, target, { env });
    assert.containsOnce(target, "img.o_user_avatar");
    assert.containsOnce(target, "span.oe_topbar_name");
    assert.strictEqual(target.querySelector(".oe_topbar_name").textContent, "Sauron (test)");
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
    await mount(UserMenu, target, { env });
    await click(target.querySelector("button.dropdown-toggle"));
    assert.containsOnce(target, ".dropdown-menu .dropdown-item");
    const item = target.querySelector(".dropdown-menu .dropdown-item");
    assert.strictEqual(item.textContent, "Preferences");
    await click(item);
    assert.verifySteps(["7", "Change My Preferences"]);
});
