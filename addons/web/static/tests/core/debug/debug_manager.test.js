import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import { regenerateAssets, becomeSuperuser } from "@web/core/debug/debug_menu_items";
import { openViewItem } from "@web/webclient/debug/debug_items";
import { describe, test, expect, beforeEach } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { DebugMenu } from "@web/core/debug/debug_menu";
import { ActionDialog } from "@web/webclient/actions/action_dialog";
import { WebClient } from "@web/webclient/webclient";
import { registry } from "@web/core/registry";
import { useDebugCategory, useOwnDebugContext } from "@web/core/debug/debug_context";
import {
    mountWithCleanup,
    contains,
    onRpc,
    patchWithCleanup,
    fields,
    models,
    webModels,
    defineWebModels,
    getService,
    defineModels,
    clearRegistry,
    serverState,
    makeDialogMockEnv,
} from "@web/../tests/web_test_helpers";
import { Component, xml } from "@odoo/owl";
import { queryOne, queryAll, queryAllTexts, click, queryAllProperties } from "@odoo/hoot-dom";

class DebugMenuParent extends Component {
    static template = xml`<DebugMenu/>`;
    static components = { DebugMenu };
    static props = ["*"];
    setup() {
        useOwnDebugContext({ categories: ["default", "custom"] });
    }
}

const debugRegistry = registry.category("debug");

onRpc(async (args) => {
    if (args.method === "has_access") {
        return true;
    }
    if (args.route === "/web/dataset/call_kw/ir.attachment/regenerate_assets_bundles") {
        expect.step("ir.attachment/regenerate_assets_bundles");
        return true;
    }
});

beforeEach(() => {
    // Remove this service to clear the debug menu from anything else than what the test insert into
    registry.category("services").remove("profiling");
    clearRegistry(debugRegistry.category("default"));
    clearRegistry(debugRegistry.category("custom"));
});

describe.tags("desktop");
describe("DebugMenu", () => {
    test("can be rendered", async () => {
        debugRegistry
            .category("default")
            .add("item_1", () => {
                return {
                    type: "item",
                    description: "Item 1",
                    callback: () => {
                        expect.step("callback item_1");
                    },
                    sequence: 10,
                    section: "a",
                };
            })
            .add("item_2", () => {
                return {
                    type: "item",
                    description: "Item 2",
                    callback: () => {
                        expect.step("callback item_2");
                    },
                    sequence: 5,
                    section: "a",
                };
            })
            .add("item_3", () => {
                return {
                    type: "item",
                    description: "Item 3",
                    callback: () => {
                        expect.step("callback item_3");
                    },
                    section: "b",
                };
            })
            .add("item_4", () => {
                return null;
            });
        await mountWithCleanup(DebugMenuParent);
        await contains("button.dropdown-toggle").click();
        expect(".dropdown-menu .dropdown-item").toHaveCount(3);
        expect(".dropdown-menu .dropdown-menu_group").toHaveCount(2);
        const children = [...queryOne(".dropdown-menu").children] || [];
        expect(children.map((el) => el.tagName)).toEqual(["DIV", "SPAN", "SPAN", "DIV", "SPAN"]);
        expect(queryAllTexts(children)).toEqual(["a", "Item 2", "Item 1", "b", "Item 3"]);

        const items = [...queryAll(".dropdown-menu .dropdown-item")] || [];
        for (const item of items) {
            await click(item);
        }

        expect.verifySteps(["callback item_2", "callback item_1", "callback item_3"]);
    });

    test("items are sorted by sequence regardless of category", async () => {
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
        await mountWithCleanup(DebugMenuParent);
        await contains("button.dropdown-toggle").click();
        const items = [...queryAll(".dropdown-menu .dropdown-item")];
        expect(items.map((el) => el.textContent)).toEqual(["Item 1", "Item 2", "Item 3", "Item 4"]);
    });

    test("Don't display the DebugMenu if debug mode is disabled", async () => {
        const env = await makeDialogMockEnv();
        await mountWithCleanup(ActionDialog, {
            env,
            props: { close: () => {} },
        });
        expect(".o_dialog").toHaveCount(1);
        expect(".o_dialog .o_debug_manager .fa-bug").toHaveCount(0);
    });

    test("Display the DebugMenu correctly in a ActionDialog if debug mode is enabled", async () => {
        debugRegistry.category("default").add("global", () => {
            return {
                type: "item",
                description: "Global 1",
                callback: () => {
                    expect.step("callback global_1");
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
                        expect.step("callback item_1");
                    },
                    sequence: 10,
                };
            })
            .add("item2", ({ customKey }) => {
                return {
                    type: "item",
                    description: "Item 2",
                    callback: () => {
                        expect.step("callback item_2");
                        expect(customKey).toBe("abc");
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
        serverState.debug = "1";
        const env = await makeDialogMockEnv();
        await mountWithCleanup(WithCustom, {
            env,
            props: { close: () => {} },
        });
        expect(".o_dialog").toHaveCount(1);
        expect(".o_dialog .o_debug_manager .fa-bug").toHaveCount(1);
        await contains(".o_dialog .o_debug_manager button").click();
        expect(".dropdown-menu .dropdown-item").toHaveCount(2);
        // Check that global debugManager elements are not displayed (global_1)
        const items = [...queryAll(".dropdown-menu .dropdown-item")] || [];
        expect(items.map((el) => el.textContent)).toEqual(["Item 1", "Item 2"]);
        for (const item of items) {
            await click(item);
        }
        expect.verifySteps(["callback item_1", "callback item_2"]);
    });

    test("can regenerate assets bundles", async () => {
        patchWithCleanup(browser.location, {
            reload: () => expect.step("reloadPage"),
        });
        debugRegistry.category("default").add("regenerateAssets", regenerateAssets);
        await mountWithCleanup(DebugMenuParent);
        await contains("button.dropdown-toggle").click();
        expect(".dropdown-menu .dropdown-item").toHaveCount(1);
        const item = queryOne(".dropdown-menu .dropdown-item");
        expect(item).toHaveText("Regenerate Assets");
        await click(item);
        await animationFrame();
        expect.verifySteps(["ir.attachment/regenerate_assets_bundles", "reloadPage"]);
    });

    test("cannot acess the Become superuser menu if not admin", async () => {
        debugRegistry.category("default").add("becomeSuperuser", becomeSuperuser);
        user.isAdmin = false;
        await mountWithCleanup(DebugMenuParent);
        await contains("button.dropdown-toggle").click();
        expect(".dropdown-menu .dropdown-item").toHaveCount(0);
    });

    test("can open a view", async () => {
        serverState.debug = "1";

        webModels.IrUiView._views.list = `<list><field name="name"/><field name="type"/></list>`;
        webModels.IrUiView._views.search = `<search/>`;
        webModels.ResPartner._views["form,1"] = `<form><div class="some_view"/></form>`;
        webModels.ResPartner._views.search = `<search/>`;

        webModels.IrUiView._records.push({
            id: 1,
            name: "formView",
            model: "res.partner",
            type: "form",
            active: true,
        });

        defineWebModels();
        registry.category("debug").category("default").add("openViewItem", openViewItem);

        await mountWithCleanup(WebClient);
        await contains(".o_debug_manager button").click();
        await contains(".dropdown-menu .dropdown-item").click();
        expect(".modal .o_list_view").toHaveCount(1);
        await contains(".modal .o_list_view .o_data_row td").click();
        expect(".modal").toHaveCount(0);
        expect(".some_view").toHaveCount(1);
    });

    test("get view: basic rendering", async () => {
        serverState.debug = "1";

        webModels.ResPartner._views.list = `<list><field name="name"/></list>`;
        webModels.ResPartner._views.search = `<search/>`;

        defineWebModels();

        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "Partners",
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        });

        await contains(".o_debug_manager button").click();
        await contains(".dropdown-menu .dropdown-item:contains('Computed Arch')").click();
        expect(".modal").toHaveCount(1);
        expect(".modal-body").toHaveText(`<list><field name="name"/></list>`);
    });

    test("can edit a pivot view", async () => {
        serverState.debug = "1";

        webModels.ResPartner._views["pivot,18"] = "<pivot></pivot>";
        webModels.ResPartner._views.search = `<search/>`;
        webModels.IrUiView._records.push({ id: 18, name: "Edit View" });
        webModels.IrUiView._views.form = `<form><field name="id"/></form>`;
        webModels.IrUiView._views.search = `<search/>`;

        defineWebModels();
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "Partners",
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "pivot"]],
        });
        await contains(".o_debug_manager button").click();
        await contains(".dropdown-menu .dropdown-item:contains('View: Pivot')").click();

        expect(".breadcrumb-item").toHaveCount(1);
        expect(".o_breadcrumb .active").toHaveCount(1);
        expect(".o_breadcrumb .active").toHaveText("Edit View");
        expect(".o_field_widget[name=id]").toHaveText("18");
        await click(".breadcrumb .o_back_button");
        await animationFrame();
        expect(".o_breadcrumb .active").toHaveCount(1);
        expect(".o_breadcrumb .active").toHaveText("Partners");
    });

    test("can edit a search view", async () => {
        serverState.debug = "1";

        webModels.ResPartner._views.list = `<list><field name="id"/></list>`;
        webModels.ResPartner._views["search,293"] = "<search></search>";
        webModels.IrUiView._records.push({ id: 293, name: "Edit View" });
        webModels.IrUiView._views.form = `<form><field name="id"/></form>`;
        webModels.IrUiView._views.search = `<search/>`;

        defineWebModels();
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "Partners",
            res_model: "res.partner",
            type: "ir.actions.act_window",
            search_view_id: [293, "some_search_view"],
            views: [[false, "list"]],
        });
        await contains(".o_debug_manager button").click();
        await contains(".dropdown-menu .dropdown-item:contains('SearchView')").click();
        expect(".breadcrumb-item").toHaveCount(1);
        expect(".o_breadcrumb .active").toHaveCount(1);
        expect(".o_breadcrumb .active").toHaveText("Edit View");
        expect(".o_field_widget[name=id]").toHaveText("293");
    });

    test("edit search view on action without search_view_id", async () => {
        serverState.debug = "1";

        webModels.ResPartner._views.list = `<list><field name="id"/></list>`;
        webModels.ResPartner._views["search,293"] = "<search></search>";
        webModels.IrUiView._records.push({ id: 293, name: "Edit View" });
        webModels.IrUiView._views.form = `<form><field name="id"/></form>`;
        webModels.IrUiView._views.search = `<search/>`;

        defineWebModels();
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "Partners",
            res_model: "res.partner",
            type: "ir.actions.act_window",
            search_view_id: false,
            views: [[false, "list"]],
        });
        await contains(".o_debug_manager button").click();
        await contains(".dropdown-menu .dropdown-item:contains('SearchView')").click();
        expect(".breadcrumb-item").toHaveCount(1);
        expect(".o_breadcrumb .active").toHaveCount(1);
        expect(".o_breadcrumb .active").toHaveText("Edit View");
        expect(".o_field_widget[name=id]").toHaveText("293");
    });

    test("cannot edit the control panel of a form view contained in a dialog without control panel.", async () => {
        serverState.debug = "1";

        webModels.ResPartner._views.form = `<form><field name="id"/></form>`;
        webModels.ResPartner._views.search = `<search/>`;

        defineWebModels();
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "Create a Partner",
            res_model: "res.partner",
            type: "ir.actions.act_window",
            target: "new",
            views: [[false, "form"]],
        });

        await contains(".o_dialog .o_debug_manager button").click();
        expect(".dropdown-menu .dropdown-item:contains('SearchView')").toHaveCount(0);
    });

    test("set defaults: basic rendering", async () => {
        serverState.debug = "1";

        webModels.ResPartner._views["form,24"] = `
            <form>
                <field name="name"/>
            </form>`;
        webModels.ResPartner._views.search = "<search/>";
        webModels.ResPartner._records.push({ id: 1000, name: "p1" });
        webModels.IrUiView._records.push({ id: 24 });

        defineWebModels();
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "Partners",
            res_model: "res.partner",
            res_id: 1000,
            type: "ir.actions.act_window",
            views: [[24, "form"]],
        });
        await contains(".o_debug_manager button").click();
        await contains(".dropdown-menu .dropdown-item:contains('Set Default Values')").click();
        expect(".modal").toHaveCount(1);
        expect(".modal select#formview_default_fields").toHaveCount(1);
        expect(".modal #formview_default_fields option").toHaveCount(2);
        expect(".modal #formview_default_fields option").toHaveCount(2);
        expect(".modal #formview_default_fields option:nth-child(1)").toHaveText("");
        expect(".modal #formview_default_fields option:nth-child(2)").toHaveText("Name = p1");
    });

    test("set defaults: click close", async () => {
        serverState.debug = "1";

        onRpc("ir.default", "set", async () => {
            throw new Error("should not create a default");
        });

        webModels.ResPartner._views["form,25"] = `
            <form>
                <field name="name"/>
            </form>`;
        webModels.ResPartner._views.search = "<search/>";
        webModels.ResPartner._records.push({ id: 1001, name: "p1" });
        webModels.IrUiView._records.push({ id: 25 });

        defineWebModels();
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "Partners",
            res_model: "res.partner",
            res_id: 1001,
            type: "ir.actions.act_window",
            views: [[25, "form"]],
        });
        await contains(".o_debug_manager button").click();
        await contains(".dropdown-menu .dropdown-item:contains('Set Default Values')").click();
        expect(".modal").toHaveCount(1);
        await contains(".modal .modal-footer button").click();
        expect(".modal").toHaveCount(0);
    });

    test("set defaults: select and save", async () => {
        expect.assertions(3);
        serverState.debug = "1";

        onRpc("ir.default", "set", async (args) => {
            expect(args.args).toEqual(["res.partner", "name", "p1", true, true, false]);
            return true;
        });

        webModels.ResPartner._views["form,26"] = `
            <form>
                <field name="name"/>
            </form>`;
        webModels.ResPartner._views.search = "<search/>";
        webModels.ResPartner._records.push({ id: 1002, name: "p1" });
        webModels.IrUiView._records.push({ id: 26 });

        defineWebModels();
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "Partners",
            res_model: "res.partner",
            res_id: 1002,
            type: "ir.actions.act_window",
            views: [[26, "form"]],
        });
        await contains(".o_debug_manager button").click();
        await contains(".dropdown-menu .dropdown-item:contains('Set Default Values')").click();
        expect(".modal").toHaveCount(1);

        await contains(".modal #formview_default_fields").select("name");
        await contains(".modal .modal-footer button:nth-child(2)").click();
        expect(".modal").toHaveCount(0);
    });

    test("fetch raw data: basic rendering", async () => {
        serverState.debug = "1";

        class Custom extends models.Model {
            _name = "custom";

            name = fields.Char();

            _records = [
                {
                    id: 1,
                    name: "custom1",
                },
            ];

            _views = {
                form: "<form></form>",
                search: "<search/>",
            };
        }

        defineWebModels();
        defineModels([Custom]);
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "Custom",
            res_model: "custom",
            res_id: 1,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        });
        await contains(".o_debug_manager button").click();
        await contains(".dropdown-menu .dropdown-item:contains(/^Data/)").click();
        expect(".modal").toHaveCount(1);
        expect(".modal-body pre").toHaveText(
            '{\n "create_date": "2019-03-11 09:30:00",\n "display_name": "custom1",\n "id": 1,\n "name": "custom1",\n "write_date": "2019-03-11 09:30:00"\n}'
        );
    });

    test("view metadata: basic rendering", async () => {
        serverState.debug = "1";

        onRpc("get_metadata", async () => {
            return [
                {
                    create_date: "2023-01-26 14:12:10",
                    create_uid: [4, "Some user"],
                    id: 1003,
                    noupdate: false,
                    write_date: "2023-01-26 14:13:31",
                    write_uid: [6, "Another User"],
                    xmlid: "abc.partner_16",
                    xmlids: [{ xmlid: "abc.partner_16", noupdate: false }],
                },
            ];
        });

        webModels.ResPartner._views.form = `<form></form>`;
        webModels.ResPartner._views.search = "<search/>";
        webModels.ResPartner._records.push({ id: 1003, name: "p1" });

        defineWebModels();
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "Partner",
            res_model: "res.partner",
            res_id: 1003,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        });
        await contains(".o_debug_manager button").click();
        await contains(".dropdown-menu .dropdown-item:contains('Metadata')").click();
        expect(".modal").toHaveCount(1);
        const contentModal = queryAll(".modal-body table tr th, .modal-body table tr td");
        expect(queryAllTexts(contentModal)).toEqual([
            "ID:",
            "1003",
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
        ]);
    });

    test("set defaults: setting default value for datetime field", async () => {
        serverState.debug = "1";

        const argSteps = [];

        onRpc("ir.default", "set", async (args) => {
            argSteps.push(args.args);
            return true;
        });

        class Partner extends models.Model {
            _name = "partner";

            datetime = fields.Datetime();
            reference = fields.Reference({ selection: [["pony", "Pony"]] });
            m2o = fields.Many2one({ relation: "pony" });

            _records = [
                {
                    id: 1,
                    display_name: "p1",
                    datetime: "2024-01-24 16:46:16",
                    reference: "pony,1",
                    m2o: 1,
                },
            ];

            _views = {
                form: `
                    <form>
                        <field name="datetime"/>
                        <field name="reference"/>
                        <field name="m2o"/>
                    </form>`,
                search: "<search/>",
            };
        }

        class Pony extends models.Model {
            _name = "pony";

            _records = [{ id: 1 }];
        }

        class IrUiView extends models.Model {
            _name = "ir.ui.view";

            name = fields.Char();
            model = fields.Char();

            _records = [{ id: 18 }];
        }

        defineModels([Partner, Pony, IrUiView]);
        await mountWithCleanup(WebClient);

        for (const field_name of ["datetime", "reference", "m2o"]) {
            await getService("action").doAction({
                name: "Partners",
                res_model: "partner",
                res_id: 1,
                type: "ir.actions.act_window",
                views: [[18, "form"]],
            });
            await contains(".o_debug_manager button").click();
            await contains(".dropdown-menu .dropdown-item:contains('Set Default Values')").click();
            expect(".modal").toHaveCount(1);

            await contains(".modal #formview_default_fields").select(field_name);
            await contains(".modal .modal-footer button:nth-child(2)").click();
            expect(".modal").toHaveCount(0);
        }

        expect(argSteps).toEqual([
            ["partner", "datetime", "2024-01-24 16:46:16", true, true, false],
            [
                "partner",
                "reference",
                { resId: 1, resModel: "pony", displayName: "pony,1" },
                true,
                true,
                false,
            ],
            ["partner", "m2o", 1, true, true, false],
        ]);
    });

    test("display model view in developer tools", async () => {
        serverState.debug = "1";
        webModels.ResPartner._views.form = `<form><field name="name"/></form>`;
        webModels.ResPartner._views.search = "<search/>";
        webModels.ResPartner._records.push({ id: 88, name: "p1" });
        webModels.IrModel._views.form = `
            <form>
                <field name="name"/>
                <field name="model"/>
            </form>`;
        webModels.IrModel._views.search = "<search/>";

        defineWebModels();
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "Partners",
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        });

        await contains(".o_debug_manager button").click();
        await contains(".dropdown-menu .dropdown-item:contains('Model:')").click();

        expect(".breadcrumb-item").toHaveCount(1);
        expect(".o_breadcrumb .active").toHaveCount(1);
        expect(".o_breadcrumb .active").toHaveText("Partner");
    });

    test("set defaults: settings default value with a very long value", async () => {
        serverState.debug = "1";

        const fooValue = "12".repeat(250);
        const argSteps = [];

        onRpc("ir.default", "set", async (args) => {
            argSteps.push(args.args);
            return true;
        });

        class Partner extends models.Model {
            _name = "partner";

            foo = fields.Char();
            description = fields.Html();
            bar = fields.Many2one({ relation: "ir.ui.view" });

            _records = [
                {
                    id: 1,
                    display_name: "p1",
                    foo: fooValue,
                    description: fooValue,
                    bar: 18,
                },
            ];

            _views = {
                form: `
                    <form>
                        <field name="foo"/>
                        <field name="description"/>
                        <field name="bar" invisible="1"/>
                    </form>`,
                search: "<search/>",
            };
        }

        class IrUiView extends models.Model {
            _name = "ir.ui.view";

            name = fields.Char();
            model = fields.Char();

            _records = [{ id: 18 }];
        }

        defineModels([Partner, IrUiView]);

        await mountWithCleanup(WebClient);

        await getService("action").doAction({
            name: "Partners",
            res_model: "partner",
            res_id: 1,
            type: "ir.actions.act_window",
            views: [[18, "form"]],
        });
        await contains(".o_debug_manager button").click();
        await contains(".dropdown-menu .dropdown-item:contains('Set Default Values')").click();
        expect(".modal").toHaveCount(1);

        expect(queryAllTexts`.modal #formview_default_fields option`).toEqual([
            "",
            "Foo = 121212121212121212121212121212121212121212121212121212121...",
            "Description = 121212121212121212121212121212121212121212121212121212121...",
        ]);

        expect(queryAllProperties(".modal #formview_default_fields option", "value")).toEqual([
            "",
            "foo",
            "description",
        ]);

        await contains(".modal #formview_default_fields").select("foo");
        await contains(".modal .modal-footer button:nth-child(2)").click();
        expect(".modal").toHaveCount(0);
        expect(argSteps).toEqual([["partner", "foo", fooValue, true, true, false]]);
    });
});
