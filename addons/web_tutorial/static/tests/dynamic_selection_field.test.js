import { describe, expect, queryAllTexts, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    defineWebModels,
    fields,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

const VIEW_TYPES = [
    ["list", "List"],
    ["form", "Form"],
    ["kanban", "Kanban"],
];

class Step extends models.Model {
    _name = "web_tutorial.step";
    view_type_selection_options = fields.Json();
    view_types = fields.Char();
    _records = [
        { id: 1, view_types: "list, kanban", view_type_selection_options: VIEW_TYPES },
        { id: 2, view_types: false, view_type_selection_options: VIEW_TYPES },
        { id: 3, view_types: false, view_type_selection_options: VIEW_TYPES.slice(1) },
    ];
}

defineWebModels();
defineModels([Step]);

async function mountSteps() {
    await mountView({
        resModel: "web_tutorial.step",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="view_types" widget="tutorial_dynamic_selection" placeholder="All views"
                    options="{'options_field': 'view_type_selection_options', 'multi_select': True}"/>
            </list>`,
    });
}

test("several values are picked among the options of the record, stored separated by commas", async () => {
    await mountSteps();
    expect(queryAllTexts(".o_data_cell[name=view_types]")).toEqual(["List, Kanban", "", ""]);

    await contains(".o_data_row:eq(1) .o_data_cell[name=view_types]").click();
    expect(".o_data_row:eq(1) .o_select_menu input").toHaveAttribute("placeholder", "All views");
    await contains(".o_data_row:eq(1) .o_select_menu input").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["List", "Form", "Kanban"]);
    await contains(".o_select_menu_item:contains(Form)").click();
    await contains(".o_list_button_save").click();
    expect(queryAllTexts(".o_data_cell[name=view_types]")).toEqual(["List, Kanban", "Form", ""]);
});

test("the options are the ones of each record", async () => {
    await mountSteps();
    await contains(".o_data_row:eq(2) .o_data_cell[name=view_types]").click();
    await contains(".o_data_row:eq(2) .o_select_menu input").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["Form", "Kanban"]);
});
