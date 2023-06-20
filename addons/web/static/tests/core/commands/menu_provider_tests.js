/** @odoo-module **/

import { createWebClient, getActionManagerServerData } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { click, getFixture, nextTick, patchWithCleanup, triggerHotkey } from "../../helpers/utils";
import { editSearchBar } from "./command_service_tests";

let serverData;
let target;
QUnit.module("Menu Command Provider", {
    async beforeEach() {
        patchWithCleanup(browser, {
            clearTimeout: () => {},
            setTimeout: (later) => {
                later();
            },
        });
        const commandCategoryRegistry = registry.category("command_categories");
        commandCategoryRegistry.add("apps", { namespace: "/" }, { sequence: 10 });
        commandCategoryRegistry.add("menu_items", { namespace: "/" }, { sequence: 20 });
        serverData = getActionManagerServerData();
        serverData.menus = {
            root: { id: "root", children: [0, 1, 2], name: "root", appID: "root" },
            0: { id: 0, children: [], name: "UglyHack", appID: 0, xmlid: "menu_0" },
            1: { id: 1, children: [], name: "Contact", appID: 1, actionID: 1001, xmlid: "menu_1" },
            2: {
                id: 2,
                children: [3, 4],
                name: "Sales",
                appID: 2,
                actionID: 1002,
                xmlid: "menu_2",
            },
            3: {
                id: 3,
                children: [],
                name: "Info",
                appID: 2,
                actionID: 1003,
                xmlid: "menu_3",
            },
            4: {
                id: 4,
                children: [],
                name: "Report",
                appID: 2,
                actionID: 1004,
                xmlid: "menu_4",
            },
        };
        serverData.actions[1003] = {
            id: 1003,
            tag: "__test__client__action__",
            target: "main",
            type: "ir.actions.client",
            params: { description: "Info" },
        };
        serverData.actions[1004] = {
            id: 1004,
            tag: "__test__client__action__",
            target: "main",
            type: "ir.actions.client",
            params: { description: "Report" },
        };

        target = getFixture();
    },
    afterEach() {},
});

QUnit.test("displays only apps if the search value is '/'", async (assert) => {
    await createWebClient({ serverData });
    assert.containsNone(target, ".o_menu_brand");

    triggerHotkey("control+k");
    await nextTick();
    await editSearchBar("/");
    assert.containsOnce(target, ".o_command_palette");
    assert.containsOnce(target, ".o_command_category");
    assert.containsN(target, ".o_command", 2);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command_name")].map((el) => el.textContent),
        ["Contact", "Sales"]
    );
});

QUnit.test("displays apps and menu items if the search value is not only '/'", async (assert) => {
    await createWebClient({ serverData });

    triggerHotkey("control+k");
    await nextTick();
    await editSearchBar("/sal");
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command", 3);
    assert.deepEqual(
        [...target.querySelectorAll(".o_command_name")].map((el) => el.textContent),
        ["Sales", "Sales / Info", "Sales / Report"]
    );
});

QUnit.test("opens an app", async (assert) => {
    await createWebClient({ serverData });
    assert.containsNone(target, ".o_menu_brand");

    triggerHotkey("control+k");
    await nextTick();
    await editSearchBar("/");
    assert.containsOnce(target, ".o_command_palette");

    triggerHotkey("enter");
    await nextTick();
    await nextTick();
    // empty screen for now, wait for actual action to show up
    await nextTick();
    assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "Contact");
    assert.strictEqual(
        target.querySelector(".test_client_action").textContent,
        " ClientAction_Id 1"
    );
});

QUnit.test("opens a menu items", async (assert) => {
    await createWebClient({ serverData });
    assert.containsNone(target, ".o_menu_brand");

    triggerHotkey("control+k");
    await nextTick();
    await editSearchBar("/sal");
    assert.containsOnce(target, ".o_command_palette");
    assert.containsN(target, ".o_command_category", 2);

    click(target, "#o_command_2");
    await nextTick();
    await nextTick();
    // empty screen for now, wait for actual action to show up
    await nextTick();
    assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "Sales");
    assert.strictEqual(
        target.querySelector(".test_client_action").textContent,
        " ClientAction_Report"
    );
});
