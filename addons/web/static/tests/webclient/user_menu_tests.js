/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui_service";
import { patch, unpatch } from "@web/core/utils/patch";
import { hotkeyService } from "@web/webclient/hotkeys/hotkey_service";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { preferencesItem } from "@web/webclient/user_menu/user_menu_items";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeLocalizationService, makeFakeUserService } from "../helpers/mock_services";
import { click, getFixture } from "../helpers/utils";

const { mount } = owl;
const serviceRegistry = registry.category("services");
const userMenuRegistry = registry.category("user_menuitems");
let target;
let env;
let userMenu;

QUnit.module("UserMenu", {
    async beforeEach() {
        serviceRegistry.add("user", makeFakeUserService({ name: "Sauron" }));
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
        target = getFixture();
        patch(browser, "usermenutest", {
            location: {
                origin: "http://lordofthering",
            },
        });
    },
    afterEach() {
        userMenu.unmount();
        unpatch(browser, "usermenutest");
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
    userMenu = await mount(UserMenu, { env, target });
    let userMenuEl = userMenu.el;
    assert.containsOnce(userMenuEl, "img.o_user_avatar");
    assert.strictEqual(
        userMenuEl.querySelector("img.o_user_avatar").src,
        "http://lordofthering/web/image?model=res.users&field=image_128&id=7"
    );
    assert.containsOnce(userMenuEl, "span.oe_topbar_name");
    assert.strictEqual(userMenuEl.querySelector(".oe_topbar_name").textContent, "Sauron");
    assert.containsNone(userMenuEl, "ul.o_dropdown_menu li.o_dropdown_item");
    await click(userMenu.el.querySelector("button.o_dropdown_toggler"));
    userMenuEl = userMenu.el;
    assert.containsN(userMenuEl, "ul.o_dropdown_menu li.o_dropdown_item", 3);
    assert.containsOnce(userMenuEl, "div.dropdown-divider");
    const children = [...(userMenuEl.querySelector("ul.o_dropdown_menu").children || [])];
    assert.deepEqual(
        children.map((el) => el.tagName),
        ["LI", "LI", "DIV", "LI"]
    );
    const items = [...userMenuEl.querySelectorAll("ul.o_dropdown_menu li.o_dropdown_item")] || [];
    assert.deepEqual(
        items.map((el) => el.dataset.menu),
        ["ring", "bad", "eye"]
    );
    const spans =
        [...userMenuEl.querySelectorAll("ul.o_dropdown_menu li.o_dropdown_item span")] || [];
    assert.deepEqual(
        spans.map((el) => el.textContent),
        ["Ring", "Bad", "Eye"]
    );
    for (const item of items) {
        click(item);
    }
    assert.verifySteps(["callback ring_item", "callback bad_item", "callback eye_item"]);
});

QUnit.test("display the correct name in debug mode", async (assert) => {
    env = await makeTestEnv({ debug: "1" });
    userMenu = await mount(UserMenu, { env, target });
    let userMenuEl = userMenu.el;
    assert.containsOnce(userMenuEl, "img.o_user_avatar");
    assert.containsOnce(userMenuEl, "span.oe_topbar_name");
    assert.strictEqual(userMenuEl.querySelector(".oe_topbar_name").textContent, "Sauron (test)");
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
    userMenu = await mount(UserMenu, { env, target });
    await click(userMenu.el.querySelector("button.o_dropdown_toggler"));
    assert.containsOnce(userMenu.el, "ul.o_dropdown_menu li.o_dropdown_item");
    const item = userMenu.el.querySelector("ul.o_dropdown_menu li.o_dropdown_item");
    assert.strictEqual(item.textContent, "Preferences");
    await click(item);
    assert.verifySteps(["7", "Change My Preferences"]);
});
