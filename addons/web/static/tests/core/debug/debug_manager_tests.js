/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { DebugMenu } from "@web/core/debug/debug_menu";
import { regenerateAssets } from "@web/core/debug/debug_menu_items";
import { registry } from "@web/core/registry";
import { useDebugCategory, useOwnDebugContext } from "@web/core/debug/debug_context";
import { ormService } from "@web/core/orm_service";
import { uiService } from "@web/core/ui/ui_service";
import { useSetupView } from "@web/views/view_hook";
import { ActionDialog } from "@web/webclient/actions/action_dialog";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { makeTestEnv, utils } from "../../helpers/mock_env";
import {
    fakeCompanyService,
    fakeCommandService,
    makeFakeDialogService,
    makeFakeLocalizationService,
    makeFakeUserService,
} from "../../helpers/mock_services";
import {
    click,
    getFixture,
    getNodesTextContent,
    legacyExtraNextTick,
    mount,
    nextTick,
    patchWithCleanup,
} from "../../helpers/utils";
import { createWebClient, doAction, getActionManagerServerData } from "../../webclient/helpers";
import { openViewItem } from "@web/webclient/debug_items";
import { editSearchView, editView, setDefaults, viewMetadata } from "@web/views/debug_items";

import { Component, xml } from "@odoo/owl";
const { prepareRegistriesWithCleanup } = utils;

export class DebugMenuParent extends Component {
    setup() {
        useOwnDebugContext({ categories: ["default", "custom"] });
    }
}
DebugMenuParent.template = xml`<DebugMenu/>`;
DebugMenuParent.components = { DebugMenu };

const debugRegistry = registry.category("debug");
let target;
let testConfig;

QUnit.module("DebugMenu", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        registry
            .category("services")
            .add("hotkey", hotkeyService)
            .add("ui", uiService)
            .add("orm", ormService)
            .add("dialog", makeFakeDialogService())
            .add("localization", makeFakeLocalizationService())
            .add("command", fakeCommandService);
        const mockRPC = async (route, args) => {
            if (args.method === "check_access_rights") {
                return Promise.resolve(true);
            }
        };
        testConfig = { mockRPC };
    });
    QUnit.test("can be rendered", async (assert) => {
        debugRegistry
            .category("default")
            .add("item_1", () => {
                return {
                    type: "item",
                    description: "Item 1",
                    callback: () => {
                        assert.step("callback item_1");
                    },
                    sequence: 10,
                };
            })
            .add("item_2", () => {
                return {
                    type: "item",
                    description: "Item 2",
                    callback: () => {
                        assert.step("callback item_2");
                    },
                    sequence: 5,
                };
            })
            .add("item_3", () => {
                return {
                    type: "item",
                    description: "Item 3",
                    callback: () => {
                        assert.step("callback item_3");
                    },
                };
            })
            .add("separator", () => {
                return {
                    type: "separator",
                    sequence: 20,
                };
            })
            .add("separator_2", () => {
                return null;
            })
            .add("item_4", () => {
                return null;
            });
        const env = await makeTestEnv(testConfig);
        await mount(DebugMenuParent, target, { env });
        await click(target.querySelector("button.dropdown-toggle"));
        assert.containsN(target, ".dropdown-menu .dropdown-item", 3);
        assert.containsOnce(target, ".dropdown-divider");
        const children = [...(target.querySelector(".dropdown-menu").children || [])];
        assert.deepEqual(
            children.map((el) => el.tagName),
            ["SPAN", "SPAN", "DIV", "SPAN"]
        );
        const items = [...target.querySelectorAll(".dropdown-menu .dropdown-item")] || [];
        assert.deepEqual(
            items.map((el) => el.textContent),
            ["Item 2", "Item 1", "Item 3"]
        );
        for (const item of items) {
            click(item);
        }
        assert.verifySteps(["callback item_2", "callback item_1", "callback item_3"]);
    });

    QUnit.test("items are sorted by sequence regardless of category", async (assert) => {
        debugRegistry
            .category("default")
            .add("item_1", () => {
                return {
                    type: "item",
                    description: "Item 4",
                    sequence: 4,
                };
            })
            .add("item_2", () => {
                return {
                    type: "item",
                    description: "Item 1",
                    sequence: 1,
                };
            });
        debugRegistry
            .category("custom")
            .add("item_1", () => {
                return {
                    type: "item",
                    description: "Item 3",
                    sequence: 3,
                };
            })
            .add("item_2", () => {
                return {
                    type: "item",
                    description: "Item 2",
                    sequence: 2,
                };
            });
        const env = await makeTestEnv(testConfig);
        await mount(DebugMenuParent, target, { env });
        await click(target.querySelector("button.dropdown-toggle"));
        const items = [...target.querySelectorAll(".dropdown-menu .dropdown-item")];
        assert.deepEqual(
            items.map((el) => el.textContent),
            ["Item 1", "Item 2", "Item 3", "Item 4"]
        );
    });

    QUnit.test("Don't display the DebugMenu if debug mode is disabled", async (assert) => {
        const env = await makeTestEnv(testConfig);
        env.dialogData = {
            isActive: true,
            close() {},
        };
        await mount(ActionDialog, target, {
            env,
            props: { close: () => {} },
        });
        assert.containsOnce(target, ".o_dialog");
        assert.containsNone(target, ".o_dialog .o_debug_manager .fa-bug");
    });

    QUnit.test(
        "Display the DebugMenu correctly in a ActionDialog if debug mode is enabled",
        async (assert) => {
            assert.expect(8);
            debugRegistry.category("default").add("global", () => {
                return {
                    type: "item",
                    description: "Global 1",
                    callback: () => {
                        assert.step("callback global_1");
                    },
                    sequence: 0,
                };
            });
            debugRegistry
                .category("custom")
                .add("item1", () => {
                    return {
                        type: "item",
                        description: "Item 1",
                        callback: () => {
                            assert.step("callback item_1");
                        },
                        sequence: 10,
                    };
                })
                .add("item2", ({ customKey }) => {
                    return {
                        type: "item",
                        description: "Item 2",
                        callback: () => {
                            assert.step("callback item_2");
                            assert.strictEqual(customKey, "abc");
                        },
                        sequence: 20,
                    };
                });
            class WithCustom extends ActionDialog {
                setup() {
                    super.setup(...arguments);
                    useDebugCategory("custom", { customKey: "abc" });
                }
            }
            patchWithCleanup(odoo, { debug: "1" });
            const env = await makeTestEnv(testConfig);
            env.dialogData = {
                isActive: true,
                close() {},
            };
            await mount(WithCustom, target, {
                env,
                props: { close: () => {} },
            });
            assert.containsOnce(target, ".o_dialog");
            assert.containsOnce(target, ".o_dialog .o_debug_manager .fa-bug");
            await click(target, ".o_dialog .o_debug_manager button");
            const debugManagerEl = target.querySelector(".o_debug_manager");
            assert.containsN(debugManagerEl, ".dropdown-menu .dropdown-item", 2);
            // Check that global debugManager elements are not displayed (global_1)
            const items =
                [...debugManagerEl.querySelectorAll(".dropdown-menu .dropdown-item")] || [];
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
        debugRegistry.category("default").add("regenerateAssets", regenerateAssets);
        const env = await makeTestEnv(testConfig);
        await mount(DebugMenuParent, target, { env });
        await click(target.querySelector("button.dropdown-toggle"));
        assert.containsOnce(target, ".dropdown-menu .dropdown-item");
        const item = target.querySelector(".dropdown-menu .dropdown-item");
        assert.strictEqual(item.textContent, "Regenerate Assets Bundles");
        await click(item);
        assert.verifySteps(["ir.attachment/search", "ir.attachment/unlink", "reloadPage"]);
    });

    QUnit.test("can open a view", async (assert) => {
        assert.expect(3);

        const mockRPC = async (route, args) => {
            if (args.method === "check_access_rights") {
                return Promise.resolve(true);
            }
        };
        prepareRegistriesWithCleanup();
        registry.category("services").add("company", fakeCompanyService);

        patchWithCleanup(odoo, {
            debug: true,
        });

        registry.category("debug").category("default").add("openViewItem", openViewItem);

        const serverData = getActionManagerServerData();
        Object.assign(serverData.models, {
            "ir.ui.view": {
                fields: {
                    model: { type: "char" },
                    name: { type: "char" },
                    type: { type: "char" },
                },
                records: [
                    {
                        id: 1,
                        name: "formView",
                        model: "partner",
                        type: "form",
                    },
                ],
            },
        });

        Object.assign(serverData.views, {
            "ir.ui.view,false,list": `<list><field name="name"/><field name="type"/></list>`,
            "ir.ui.view,false,search": `<search/>`,
            "partner,1,form": `<form><div class="some_view"/></form>`,
        });

        await createWebClient({ serverData, mockRPC });
        await click(target.querySelector(".o_debug_manager button"));
        await click(target.querySelector(".o_debug_manager .dropdown-item"));
        assert.containsOnce(target, ".modal .o_list_view");

        await click(target.querySelector(".modal .o_list_view .o_data_row td"));
        assert.containsNone(target, ".modal");
        assert.containsOnce(target, ".some_view");
    });

    QUnit.test("can edit a pivot view", async (assert) => {
        const mockRPC = async (route, args) => {
            if (args.method === "check_access_rights") {
                return Promise.resolve(true);
            }
        };
        prepareRegistriesWithCleanup();

        patchWithCleanup(odoo, {
            debug: true,
        });

        registry.category("services").add("user", makeFakeUserService());
        registry.category("debug").category("view").add("editViewItem", editView);

        const serverData = getActionManagerServerData();
        serverData.actions[1234] = {
            id: 1234,
            xml_id: "action_1234",
            name: "Reporting Ponies",
            res_model: "pony",
            type: "ir.actions.act_window",
            views: [[18, "pivot"]],
        };
        serverData.views["pony,18,pivot"] = "<pivot></pivot>";
        serverData.models["ir.ui.view"] = {
            fields: {},
            records: [{ id: 18 }],
        };
        serverData.views["ir.ui.view,false,form"] = `<form><field name="id"/></form>`;

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1234);
        await click(target.querySelector(".o_debug_manager button"));
        await click(target.querySelector(".o_debug_manager .dropdown-item"));
        assert.containsOnce(target, ".modal .o_form_view");
        assert.strictEqual(
            target.querySelector(".modal .o_form_view .o_field_widget[name=id] input").value,
            "18"
        );
    });

    QUnit.test("can edit a search view", async (assert) => {
        const mockRPC = async (route, args) => {
            if (args.method === "check_access_rights") {
                return Promise.resolve(true);
            }
        };
        prepareRegistriesWithCleanup();
        registry.category("services").add("company", fakeCompanyService);

        patchWithCleanup(odoo, {
            debug: true,
        });

        registry.category("debug").category("view").add("editSearchViewItem", editSearchView);

        const serverData = getActionManagerServerData();

        serverData.views["partner,293,search"] = "<search></search>";
        serverData.actions[1].search_view_id = [293, "some_search_view"];
        serverData.models["ir.ui.view"] = {
            fields: {},
            records: [{ id: 293 }],
        };
        serverData.views["ir.ui.view,false,form"] = `<form><field name="id"/></form>`;

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);
        await click(target.querySelector(".o_debug_manager button"));
        await click(target.querySelector(".o_debug_manager .dropdown-item"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".modal .o_form_view");
        assert.strictEqual(
            target.querySelector(".modal .o_form_view .o_field_widget[name=id] input").value,
            "293"
        );
    });

    QUnit.test("edit search view on action without search_view_id", async (assert) => {
        // When the kanban view will be converted to Owl, this test could be simplified by
        // removing the toy view and using the kanban view directly
        prepareRegistriesWithCleanup();

        class ToyController extends Component {
            setup() {
                useSetupView();
            }
        }
        ToyController.template = xml`<div class="o-toy-view"/>`;

        registry.category("views").add("toy", {
            type: "toy",
            display_name: "toy view",
            Controller: ToyController,
        });

        const mockRPC = async (route, args) => {
            if (args.method === "check_access_rights") {
                return Promise.resolve(true);
            }
        };

        patchWithCleanup(odoo, {
            debug: true,
        });

        registry.category("debug").category("view").add("editSearchViewItem", editSearchView);

        const serverData = getActionManagerServerData();
        serverData.actions[1] = {
            id: 1,
            xml_id: "action_1",
            name: "Partners Action 1",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "toy"]],
            search_view_id: false,
        };
        serverData.models["ir.ui.view"] = {
            fields: {},
            records: [{ id: 293 }],
        };
        serverData.views = {};
        serverData.views["ir.ui.view,false,form"] = `<form><field name="id"/></form>`;
        serverData.views["partner,false,toy"] = `<toy></toy>`;
        serverData.views["partner,293,search"] = `<search></search>`;

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);
        assert.containsOnce(target, ".o-toy-view");

        await click(target.querySelector(".o_debug_manager button"));
        await click(target.querySelector(".o_debug_manager .dropdown-item"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".modal .o_form_view");
        assert.strictEqual(
            target.querySelector(".modal .o_form_view .o_field_widget[name=id] input").value,
            "293"
        );
    });

    QUnit.test(
        "cannot edit the control panel of a form view contained in a dialog without control panel.",
        async (assert) => {
            const mockRPC = async (route, args) => {
                if (args.method === "check_access_rights") {
                    return Promise.resolve(true);
                }
            };
            prepareRegistriesWithCleanup();

            patchWithCleanup(odoo, {
                debug: true,
            });
            registry.category("debug").category("view").add("editSearchViewItem", editSearchView);

            const serverData = getActionManagerServerData();

            const webClient = await createWebClient({ serverData, mockRPC });
            // opens a form view in a dialog without a control panel.
            await doAction(webClient, 5);
            await click(target.querySelector(".o_dialog .o_debug_manager button"));
            assert.containsNone(target, ".o_debug_manager .dropdown-item");
        }
    );

    QUnit.test("set defaults: basic rendering", async (assert) => {
        prepareRegistriesWithCleanup();
        patchWithCleanup(odoo, {
            debug: true,
        });

        registry.category("services").add("user", makeFakeUserService());
        registry.category("debug").category("form").add("setDefaults", setDefaults);

        const serverData = getActionManagerServerData();
        serverData.actions[1234] = {
            id: 1234,
            xml_id: "action_1234",
            name: "Partners",
            res_model: "partner",
            res_id: 1,
            type: "ir.actions.act_window",
            views: [[18, "form"]],
        };
        serverData.views["partner,18,form"] = `
            <form>
                <field name="m2o"/>
                <field name="foo"/>
                <field name="o2m"/>
            </form>`;
        serverData.models["ir.ui.view"] = {
            fields: {},
            records: [{ id: 18 }],
        };
        serverData.models.partner.records = [{ id: 1, display_name: "p1", foo: "hello" }];

        const mockRPC = async (route, args) => {
            if (args.method === "check_access_rights") {
                return Promise.resolve(true);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1234);
        await click(target.querySelector(".o_debug_manager button"));
        await click(target.querySelector(".o_debug_manager .dropdown-item"));
        assert.containsOnce(target, ".modal");
        assert.containsOnce(target, ".modal select#formview_default_fields");
        assert.containsN(target.querySelector(".modal #formview_default_fields"), "option", 2);
        const options = target.querySelectorAll(".modal #formview_default_fields option");
        assert.strictEqual(options[0].value, "");
        assert.strictEqual(options[1].value, "foo");
    });

    QUnit.test("set defaults: click close", async (assert) => {
        prepareRegistriesWithCleanup();
        patchWithCleanup(odoo, {
            debug: true,
        });

        registry.category("services").add("user", makeFakeUserService());
        registry.category("debug").category("form").add("setDefaults", setDefaults);

        const serverData = getActionManagerServerData();
        serverData.actions[1234] = {
            id: 1234,
            xml_id: "action_1234",
            name: "Partners",
            res_model: "partner",
            res_id: 1,
            type: "ir.actions.act_window",
            views: [[18, "form"]],
        };
        serverData.views["partner,18,form"] = `
            <form>
                <field name="foo"/>
            </form>`;
        serverData.models["ir.ui.view"] = {
            fields: {},
            records: [{ id: 18 }],
        };
        serverData.models.partner.records = [{ id: 1, display_name: "p1", foo: "hello" }];

        const mockRPC = async (route, args) => {
            if (args.method === "set" && args.model === "ir.default") {
                throw new Error("should not create a default");
            }
            if (args.method === "check_access_rights") {
                return Promise.resolve(true);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1234);
        await click(target.querySelector(".o_debug_manager button"));
        await click(target.querySelector(".o_debug_manager .dropdown-item"));
        assert.containsOnce(target, ".modal");

        await click(target.querySelector(".modal .modal-footer button"));
        assert.containsNone(target, ".modal");
    });

    QUnit.test("set defaults: select and save", async (assert) => {
        assert.expect(3);

        prepareRegistriesWithCleanup();
        patchWithCleanup(odoo, {
            debug: true,
        });

        registry.category("services").add("user", makeFakeUserService());
        registry.category("debug").category("form").add("setDefaults", setDefaults);

        const serverData = getActionManagerServerData();
        serverData.actions[1234] = {
            id: 1234,
            xml_id: "action_1234",
            name: "Partners",
            res_model: "partner",
            res_id: 1,
            type: "ir.actions.act_window",
            views: [[18, "form"]],
        };
        serverData.views["partner,18,form"] = `
            <form>
                <field name="foo"/>
            </form>`;
        serverData.models["ir.ui.view"] = {
            fields: {},
            records: [{ id: 18 }],
        };
        serverData.models.partner.records = [{ id: 1, display_name: "p1", foo: "hello" }];

        const mockRPC = async (route, args) => {
            if (args.method === "check_access_rights") {
                return Promise.resolve(true);
            }
            if (args.method === "set" && args.model === "ir.default") {
                assert.deepEqual(args.args, ["partner", "foo", "hello", true, true, false]);
                return true;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1234);
        await click(target.querySelector(".o_debug_manager button"));
        await click(target.querySelector(".o_debug_manager .dropdown-item"));
        assert.containsOnce(target, ".modal");

        const select = target.querySelector(".modal #formview_default_fields");
        select.value = "foo";
        select.dispatchEvent(new Event("change"));
        await nextTick();
        await click(target.querySelectorAll(".modal .modal-footer button")[1]);
        assert.containsNone(target, ".modal");
    });

    QUnit.test("view metadata: basic rendering", async (assert) => {
        prepareRegistriesWithCleanup();
        patchWithCleanup(odoo, {
            debug: true,
        });

        registry.category("services").add("user", makeFakeUserService());
        registry.category("debug").category("form").add("viewMetadata", viewMetadata);

        const serverData = getActionManagerServerData();
        serverData.actions[1234] = {
            id: 1234,
            xml_id: "action_1234",
            name: "Partners",
            res_model: "partner",
            res_id: 27,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
        serverData.models.partner.records = [{ id: 27, display_name: "p1" }];

        const mockRPC = async (route, args) => {
            if (args.method === "check_access_rights") {
                return Promise.resolve(true);
            }
            if (args.method === "get_metadata") {
                return [
                    {
                        create_date: "2023-01-26 14:12:10",
                        create_uid: [4, "Some user"],
                        id: 27,
                        noupdate: false,
                        write_date: "2023-01-26 14:13:31",
                        write_uid: [6, "Another User"],
                        xmlid: "abc.partner_16",
                        xmlids: [{ xmlid: "abc.partner_16", noupdate: false }],
                    },
                ];
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1234);
        await click(target.querySelector(".o_debug_manager button"));
        await click(target.querySelector(".o_debug_manager .dropdown-item"));
        assert.containsOnce(target, ".modal");
        assert.deepEqual(
            getNodesTextContent(
                target.querySelectorAll(".modal-body table tr th, .modal-body table tr td")
            ),
            [
                "ID:",
                "27",
                "XML ID:",
                "abc.partner_16",
                "No Update:",
                "false (change)",
                "Creation User:",
                "Some user",
                "Creation Date:",
                "01/26/2023 15:12:10",
                "Latest Modification by:",
                "Another User",
                "Latest Modification Date:",
                "01/26/2023 15:13:31",
            ]
        );
    });
});
