import { BurgerUserMenu } from "@web/webclient/burger_menu/burger_user_menu/burger_user_menu";
import { preferencesItem } from "@web/webclient/user_menu/user_menu_items";
import { registry } from "@web/core/registry";

import {
    clearRegistry,
    mockService,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { beforeEach, expect, test } from "@odoo/hoot";
import { click, queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { markup } from "@odoo/owl";

const userMenuRegistry = registry.category("user_menuitems");

beforeEach(() => clearRegistry(userMenuRegistry));

test.tags("mobile");
test("can be rendered", async () => {
    userMenuRegistry.add("bad_item", () => ({
        type: "item",
        id: "bad",
        description: "Bad",
        callback: () => {
            expect.step("callback bad_item");
        },
        sequence: 10,
    }));
    userMenuRegistry.add("ring_item", () => ({
        type: "item",
        id: "ring",
        description: "Ring",
        callback: () => {
            expect.step("callback ring_item");
        },
        sequence: 5,
    }));
    userMenuRegistry.add("frodo_item", () => ({
        type: "switch",
        id: "frodo",
        description: "Frodo",
        callback: () => {
            expect.step("callback frodo_item");
        },
        sequence: 11,
    }));
    userMenuRegistry.add("separator", () => ({
        type: "separator",
        sequence: 15,
    }));
    userMenuRegistry.add("invisible_item", () => ({
        type: "item",
        id: "hidden",
        description: "Hidden Power",
        callback: () => {
            expect.step("callback hidden_item");
        },
        sequence: 5,
        hide: true,
    }));
    userMenuRegistry.add("eye_item", () => ({
        type: "item",
        id: "eye",
        description: "Eye",
        callback: () => {
            expect.step("callback eye_item");
        },
    }));
    userMenuRegistry.add("html_item", () => ({
        type: "item",
        id: "html",
        description: markup`<div>HTML<i class="fa fa-check px-2"></i></div>`,
        callback: () => {
            expect.step("callback html_item");
        },
        sequence: 20,
    }));
    await mountWithCleanup(BurgerUserMenu);
    expect("a").toHaveCount(4);
    expect(".form-switch input.form-check-input").toHaveCount(1);
    expect("hr").toHaveCount(1);
    expect(queryAllTexts("a, .form-switch")).toEqual(["Ring", "Bad", "Frodo", "HTML", "Eye"]);
    for (const item of queryAll("a, .form-switch")) {
        await click(item);
    }
    expect.verifySteps([
        "callback ring_item",
        "callback bad_item",
        "callback frodo_item",
        "callback html_item",
        "callback eye_item",
    ]);
});

test.tags("mobile");
test("can execute the callback of settings", async () => {
    onRpc("action_get", () => ({
        name: "Change My Preferences",
        res_id: 0,
    }));
    mockService("action", {
        async doAction(actionId) {
            expect.step(actionId.res_id);
            expect.step(actionId.name);
            return true;
        },
    });
    userMenuRegistry.add("preferences", preferencesItem);
    await mountWithCleanup(BurgerUserMenu);
    expect("a").toHaveCount(1);
    expect("a").toHaveText("My Preferences");
    await click("a");
    await expect.waitForSteps([7, "Change My Preferences"]);
});
