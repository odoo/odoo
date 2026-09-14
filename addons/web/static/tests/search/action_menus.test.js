// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";

import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    stepAllNetworkCalls,
} from "../web_test_helpers.js";

class Foo extends models.Model {
    _name = "foo";

    value = fields.Boolean();

    _records = [
        {
            id: 1,
            value: true,
        },
        {
            id: 2,
            value: false,
        },
    ];
}

class IrActionsReport extends models.Model {
    _name = "ir.actions.report";

    get_valid_action_reports(
        /** @type {any} */ self,
        /** @type {any} */ model,
        /** @type {any} */ recordIds,
    ) {
        const validActionIds = [1];
        if (recordIds.includes(1)) {
            validActionIds.push(2);
        }
        if (recordIds.includes(2)) {
            validActionIds.push(3);
        }
        if (!recordIds.includes(1) && !recordIds.includes(2)) {
            validActionIds.push(3);
        }
        return validActionIds;
    }
}

defineModels([Foo, IrActionsReport]);

describe.current.tags("desktop");

const printItems = [
    {
        id: 1,
        name: "Some Report always visible",
        type: "ir.actions.action_report",
        domain: "",
    },
    {
        id: 2,
        name: "Some Report with domain 1",
        type: "ir.actions.action_report",
        domain: [["value", "=", "True"]],
    },
    {
        id: 3,
        name: "Some Report with domain 2",
        type: "ir.actions.action_report",
        domain: [["value", "=", "False"]],
    },
];

test("render ActionMenus in list view", async () => {
    stepAllNetworkCalls();
    await mountView({
        type: "list",
        resModel: "foo",
        actionMenus: {
            action: [],
            print: printItems,
        },
        loadActionMenus: true,
        arch: `
              <list>
                  <field name="value"/>
              </list>
         `,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
    ]);

    await contains(`thead .o_list_record_selector input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(
        queryAllTexts(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`),
    ).toEqual(["Print", "Actions"]);

    await contains(`.o_cp_action_menus .dropdown-toggle:eq(0)`).click();
    expect(`.o-dropdown--menu .o-dropdown-item`).toHaveCount(3);
    expect(queryAllTexts(`.o-dropdown--menu .o-dropdown-item`)).toEqual([
        "Some Report always visible",
        "Some Report with domain 1",
        "Some Report with domain 2",
    ]);

    expect.verifySteps(["get_valid_action_reports"]);

    await contains(`.o_data_row:eq(1) input`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle:eq(0)`).click();
    expect(`.o-dropdown--menu .o-dropdown-item`).toHaveCount(2);
    expect(queryAllTexts(`.o-dropdown--menu .o-dropdown-item`)).toEqual([
        "Some Report always visible",
        "Some Report with domain 1",
    ]);

    expect.verifySteps(["get_valid_action_reports"]);
});

test("render ActionMenus in form view", async () => {
    stepAllNetworkCalls();
    await mountView({
        type: "form",
        resModel: "foo",
        resId: 1,
        actionMenus: {
            action: [],
            print: printItems,
        },
        loadActionMenus: true,
        arch: `
              <form>
                  <field name="value"/>
              </form>
         `,
    });
    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_read",
    ]);

    await contains(`div.o_control_panel_breadcrumbs_actions i.fa-cog`).click();

    await contains(`button.o-dropdown:contains(Print)`).click();
    expect(queryAllTexts(`.o-dropdown--menu-submenu span.o-dropdown-item`)).toEqual([
        "Some Report always visible",
        "Some Report with domain 1",
    ]);

    expect.verifySteps(["get_valid_action_reports"]);

    await contains(`button.o_form_button_create`).click();
    await contains(`button.o_form_button_save`).click();
    expect(`.o_pager_counter`).toHaveText("2 / 2");
    expect.verifySteps(["onchange", "web_save"]);
    await contains(`div.o_control_panel_breadcrumbs_actions i.fa-cog`).click();
    await contains(`button.o-dropdown:contains(Print)`).click();
    expect(queryAllTexts(`.o-dropdown--menu-submenu span.o-dropdown-item`)).toEqual([
        "Some Report always visible",
        "Some Report with domain 2",
    ]);
    expect.verifySteps(["get_valid_action_reports"]);

    await contains(`.o_pager_previous`).click();
    expect(`.o_pager_counter`).toHaveText("1 / 2");
    await contains(`div.o_control_panel_breadcrumbs_actions i.fa-cog`).click();
    await contains(`button.o-dropdown:contains(Print)`).click();
    expect(queryAllTexts(`.o-dropdown--menu-submenu span.o-dropdown-item`)).toEqual([
        "Some Report always visible",
        "Some Report with domain 1",
    ]);
    expect.verifySteps(["web_read", "get_valid_action_reports"]);
});

test("render ActionMenus in list view with extraPrintItems", async () => {
    stepAllNetworkCalls();
    const listView = registry.category("views").get("list");
    class ExtraPrintController extends listView.Controller {
        get actionMenuProps() {
            return {
                ...super.actionMenuProps,
                loadExtraPrintItems: () => [
                    {
                        key: "extra_print_key",
                        description: "Extra Print Item",
                        class: "o_menu_item",
                    },
                ],
            };
        }
    }
    registry.category("views").add("extra_print", {
        ...listView,
        Controller: ExtraPrintController,
    });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list js_class="extra_print"><field name="value"/></list>`,
        actionMenus: {
            action: [],
            print: printItems,
        },
    });

    expect.verifySteps([
        "/web/webclient/translations",
        "/web/webclient/load_menus",
        "get_views",
        "web_search_read",
    ]);

    await contains(`thead .o_list_record_selector input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(
        queryAllTexts(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`),
    ).toEqual(["Print", "Actions"]);

    await contains(`.o_cp_action_menus .dropdown-toggle:eq(0)`).click();
    expect(`.o-dropdown--menu .o-dropdown-item`).toHaveCount(4);
    expect(queryAllTexts(`.o-dropdown--menu .o-dropdown-item`)).toEqual([
        "Extra Print Item",
        "Some Report always visible",
        "Some Report with domain 1",
        "Some Report with domain 2",
    ]);

    expect.verifySteps(["get_valid_action_reports"]);

    await contains(`.o_data_row:eq(1) input`).click();
    await contains(`.o_cp_action_menus .dropdown-toggle:eq(0)`).click();
    expect(`.o-dropdown--menu .o-dropdown-item`).toHaveCount(3);
    expect(queryAllTexts(`.o-dropdown--menu .o-dropdown-item`)).toEqual([
        "Extra Print Item",
        "Some Report always visible",
        "Some Report with domain 1",
    ]);

    expect.verifySteps(["get_valid_action_reports"]);
});

test("static action items are properly ordered and styled", async () => {
    await mountView({
        type: "list",
        resModel: "foo",
        actionMenus: {
            action: [],
            print: [],
        },
        loadActionMenus: true,
        arch: `
              <list>
                  <field name="value"/>
              </list>
         `,
    });
    await contains(`thead .o_list_record_selector input`).click();
    expect(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`).toHaveCount(1);
    await contains(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`).click();

    expect(queryAllTexts(`.o_menu_item`)).toEqual(["Export…", "Duplicate", "Delete"]);
    expect(`.o_menu_item:last`).toHaveClass("text-danger");
});

test("dividers separate sections and never lead the menu", async () => {
    await mountView({
        type: "list",
        resModel: "foo",
        actionMenus: { action: [], print: [] },
        loadActionMenus: true,
        arch: `
              <list>
                  <field name="value"/>
              </list>
         `,
    });
    await contains(`thead .o_list_record_selector input`).click();
    await contains(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`).click();

    expect(`.o-dropdown--menu .dropdown-divider`).toHaveCount(2);
    expect(`.o-dropdown--menu > *:first`).toHaveClass("o_menu_item");
    expect(`.o-dropdown--menu > *:last`).toHaveClass("text-danger");
});
