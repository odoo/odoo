import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    stepAllNetworkCalls,
} from "../web_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";

/** Foo is dummy model to test `action.report` with domain of its field `value`. **/
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

    get_valid_action_reports(self, model, recordIds) {
        const validActionIds = [1];
        if (recordIds.includes(1)) {
            validActionIds.push(2);
        }
        if (recordIds.includes(2)) {
            validActionIds.push(3);
        }
        if (!recordIds.includes(1) && !recordIds.includes(2)) {
            // new record are initialized with value=False so domain of action 3 is satisfied
            validActionIds.push(3);
        }
        return validActionIds;
    }
}

defineModels([Foo, IrActionsReport]);

describe.current.tags("desktop");

beforeEach(() => {
    onRpc("has_group", () => true);
});

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
        arch: /* xml */ `
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
        "has_group",
    ]);

    // select all records
    await contains(`thead .o_list_record_selector input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(queryAllTexts(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`)).toEqual([
        "Print",
        "Actions",
    ]);

    // select Print dropdown
    await contains(`.o_cp_action_menus .dropdown-toggle:eq(0)`).click();
    expect(`.o-dropdown--menu .o-dropdown-item`).toHaveCount(3);
    expect(queryAllTexts(`.o-dropdown--menu .o-dropdown-item`)).toEqual([
        "Some Report always visible",
        "Some Report with domain 1",
        "Some Report with domain 2",
    ]);

    // the last RPC call to retrieve print items only happens when the dropdown is clicked
    expect.verifySteps(["get_valid_action_reports"]);

    // select only the record that satisfies domain 1
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
        arch: /* xml */ `
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

    // select CogMenu
    await contains(`div.o_control_panel_breadcrumbs_actions i.fa-cog`).click();

    // select Print dropdown
    await contains(`button.o-dropdown:contains(Print)`).click();
    expect(queryAllTexts(`.o-dropdown--menu-submenu span.o-dropdown-item`)).toEqual([
        "Some Report always visible",
        "Some Report with domain 1",
    ]);

    // the RPC call to retrieve print items only happens when the dropdown is clicked
    expect.verifySteps(["get_valid_action_reports"]);

    // create a new record
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

    // switch back to first record
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
                loadExtraPrintItems: () => {
                    return [
                        {
                            key: "extra_print_key",
                            description: "Extra Print Item",
                            class: "o_menu_item",
                        },
                    ];
                },
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
        "has_group",
    ]);

    // select all records
    await contains(`thead .o_list_record_selector input`).click();
    expect(`div.o_control_panel .o_cp_action_menus`).toHaveCount(1);
    expect(queryAllTexts(`div.o_control_panel .o_cp_action_menus .dropdown-toggle`)).toEqual([
        "Print",
        "Actions",
    ]);

    // select Print dropdown
    await contains(`.o_cp_action_menus .dropdown-toggle:eq(0)`).click();
    expect(`.o-dropdown--menu .o-dropdown-item`).toHaveCount(4);
    expect(queryAllTexts(`.o-dropdown--menu .o-dropdown-item`)).toEqual([
        "Extra Print Item",
        "Some Report always visible",
        "Some Report with domain 1",
        "Some Report with domain 2",
    ]);

    // the last RPC call to retrieve print items only happens when the dropdown is clicked
    expect.verifySteps(["get_valid_action_reports"]);

    // select only the record that satisfies domain 1
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
