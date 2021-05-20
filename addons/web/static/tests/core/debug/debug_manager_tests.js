/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { DebugManager, useDebugManager } from "@web/core/debug/debug_menu";
import { regenerateAssets } from "@web/core/debug/debug_menu_items";
import { registry } from "@web/core/registry";
import { debugService } from "@web/core/debug/debug_service";
import { ormService } from "@web/core/orm_service";
import { uiService } from "@web/core/ui_service";
import { ActionDialog } from "@web/webclient/actions/action_dialog";
import { hotkeyService } from "@web/webclient/hotkeys/hotkey_service";
import { registerCleanup } from "../../helpers/cleanup";
import { makeTestEnv } from "../../helpers/mock_env";
import { makeFakeLocalizationService } from "../../helpers/mock_services";
import { click, getFixture, patchWithCleanup } from "../../helpers/utils";

const { Component, hooks, mount, tags } = owl;
const { useSubEnv } = hooks;

const debugRegistry = registry.category("debug");
let target;
let testConfig;

QUnit.module("DebugManager", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        registry
            .category("services")
            .add("hotkey", hotkeyService)
            .add("ui", uiService)
            .add("orm", ormService)
            .add("debug", debugService);
        const mockRPC = async (route, args) => {
            if (args.method === "check_access_rights") {
                return Promise.resolve(true);
            }
        };
        testConfig = { mockRPC };
    });
    QUnit.test("can be rendered", async (assert) => {
        debugRegistry.add("item_1", () => {
            return {
                type: "item",
                description: "Item 1",
                callback: () => {
                    assert.step("callback item_1");
                },
                sequence: 10,
            };
        });
        debugRegistry.add("item_2", () => {
            return {
                type: "item",
                description: "Item 2",
                callback: () => {
                    assert.step("callback item_2");
                },
                sequence: 5,
            };
        });
        debugRegistry.add("item_3", () => {
            return {
                type: "item",
                description: "Item 3",
                callback: () => {
                    assert.step("callback item_3");
                },
            };
        });
        debugRegistry.add("separator", () => {
            return {
                type: "separator",
                sequence: 20,
            };
        });
        debugRegistry.add("separator_2", () => {
            return {
                type: "separator",
                sequence: 7,
                hide: true,
            };
        });
        debugRegistry.add("item_4", () => {
            return {
                type: "item",
                description: "Item 4",
                callback: () => {
                    assert.step("callback item_4");
                },
                hide: true,
                sequence: 10,
            };
        });
        const env = await makeTestEnv(testConfig);
        const debugManager = await mount(DebugManager, { env, target });
        registerCleanup(() => debugManager.destroy());
        let debugManagerEl = debugManager.el;
        await click(debugManager.el.querySelector("button.o_dropdown_toggler"));
        debugManagerEl = debugManager.el;
        assert.containsN(debugManagerEl, "ul.o_dropdown_menu li.o_dropdown_item", 3);
        assert.containsOnce(debugManagerEl, "div.dropdown-divider");
        const children = [...(debugManagerEl.querySelector("ul.o_dropdown_menu").children || [])];
        assert.deepEqual(
            children.map((el) => el.tagName),
            ["LI", "LI", "DIV", "LI"]
        );
        const items =
            [...debugManagerEl.querySelectorAll("ul.o_dropdown_menu li.o_dropdown_item span")] ||
            [];
        assert.deepEqual(
            items.map((el) => el.textContent),
            ["Item 2", "Item 1", "Item 3"]
        );
        for (const item of items) {
            click(item);
        }
        assert.verifySteps(["callback item_2", "callback item_1", "callback item_3"]);
    });

    QUnit.test("Don't display the DebugManager if debug mode is disabled", async (assert) => {
        const dialogContainer = document.createElement("div");
        dialogContainer.classList.add("o_dialog_container");
        target.append(dialogContainer);
        const env = await makeTestEnv(testConfig);
        const actionDialog = await mount(ActionDialog, { env, target, props: {} });
        registerCleanup(() => {
            actionDialog.destroy();
            target.querySelector(".o_dialog_container").remove();
        });
        assert.containsOnce(target, "div.o_dialog_container .o_dialog");
        assert.containsNone(target, ".o_dialog .o_debug_manager .fa-bug");
    });

    QUnit.test(
        "Display the DebugManager correctly in a ActionDialog if debug mode is enabled",
        async (assert) => {
            const dialogContainer = document.createElement("div");
            dialogContainer.classList.add("o_dialog_container");
            target.append(dialogContainer);
            debugRegistry.add("global", () => {
                return {
                    type: "item",
                    description: "Global 1",
                    callback: () => {
                        assert.step("callback global_1");
                    },
                    sequence: 0,
                };
            });
            const item1 = {
                type: "item",
                description: "Item 1",
                callback: () => {
                    assert.step("callback item_1");
                },
                sequence: 10,
            };
            const item2 = {
                type: "item",
                description: "Item 2",
                callback: () => {
                    assert.step("callback item_2");
                },
                sequence: 20,
            };
            class Parent extends Component {
                setup() {
                    useSubEnv({ inDialog: true });
                    useDebugManager(() => [item1, item2]);
                }
            }
            Parent.components = { ActionDialog };
            Parent.template = tags.xml`<ActionDialog/>`;
            testConfig.debug = "1";
            const env = await makeTestEnv(testConfig);
            const actionDialog = await mount(Parent, { env, target });
            registerCleanup(() => {
                actionDialog.destroy();
                target.querySelector(".o_dialog_container").remove();
            });
            assert.containsOnce(target, "div.o_dialog_container .o_dialog");
            assert.containsOnce(target, ".o_dialog .o_debug_manager .fa-bug");
            await click(target, ".o_dialog .o_debug_manager button");
            const debugManagerEl = target.querySelector(".o_dialog_container .o_debug_manager");
            assert.containsN(debugManagerEl, "ul.o_dropdown_menu li.o_dropdown_item", 2);
            // Check that global debugManager elements are not displayed (global_1)
            const items =
                [
                    ...debugManagerEl.querySelectorAll(
                        "ul.o_dropdown_menu li.o_dropdown_item span"
                    ),
                ] || [];
            assert.deepEqual(
                items.map((el) => el.textContent),
                ["Item 1", "Item 2"]
            );
            for (const item of items) {
                click(item);
            }
            assert.verifySteps(["callback item_1", "callback item_2"]);
        }
    );

    QUnit.test("can regenerate assets bundles", async (assert) => {
        const mockRPC = async (route, args) => {
            if (args.method === "check_access_rights") {
                return Promise.resolve(true);
            }
            if (route === "/web/dataset/call_kw/ir.attachment/search") {
                assert.step("ir.attachment/search");
                return [1, 2, 3];
            }
            if (route === "/web/dataset/call_kw/ir.attachment/unlink") {
                assert.step("ir.attachment/unlink");
                return Promise.resolve(true);
            }
        };
        testConfig = { mockRPC };
        patchWithCleanup(browser, {
            location: {
                reload: () => assert.step("reloadPage"),
            },
        });
        registry.category("services").add("localization", makeFakeLocalizationService());
        debugRegistry.add("regenerateAssets", regenerateAssets);
        const env = await makeTestEnv(testConfig);
        const debugManager = await mount(DebugManager, { env, target });
        registerCleanup(() => debugManager.destroy());
        await click(debugManager.el.querySelector("button.o_dropdown_toggler"));
        assert.containsOnce(debugManager.el, "ul.o_dropdown_menu li.o_dropdown_item");
        const item = debugManager.el.querySelector("ul.o_dropdown_menu li.o_dropdown_item span");
        assert.strictEqual(item.textContent, "Regenerate Assets Bundles");
        await click(item);
        assert.verifySteps(["ir.attachment/search", "ir.attachment/unlink", "reloadPage"]);
    });
});
