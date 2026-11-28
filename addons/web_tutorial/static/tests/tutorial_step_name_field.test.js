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

class Step extends models.Model {
    _name = "web_tutorial.step";
    name = fields.Char();
    name_selection_options = fields.Json();
    res_model = fields.Char();
    type = fields.Selection({
        selection: [
            ["field", "Field"],
            ["method", "Method"],
            ["generic_button", "Generic Button"],
        ],
    });
    _records = [
        { id: 1, name: "name", res_model: "res.partner", type: "field" },
        {
            id: 2,
            name: "New",
            name_selection_options: [
                ["New", "New"],
                ["Archive", "Archive"],
            ],
            res_model: "res.partner",
            type: "generic_button",
        },
        { id: 3, name: "action_check", res_model: "res.partner", type: "method" },
    ];
}

class Order extends models.Model {
    _name = "tuto.order";
    partner_id = fields.Many2one({ relation: "res.partner" });
    line_ids = fields.One2many({ relation: "tuto.order.line" });
}

class OrderLine extends models.Model {
    _name = "tuto.order.line";
    name = fields.Char();
}

defineWebModels();
defineModels([Step, Order, OrderLine]);

async function mountSteps() {
    await mountView({
        resModel: "web_tutorial.step",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="type"/>
                <field name="name" widget="tutorial_step_name"/>
            </list>`,
    });
}

test("the name of a step is picked depending on its type, in the same column", async () => {
    await mountSteps();
    await contains(".o_data_row:eq(0) .o_data_cell[name=name]").click();
    expect(".o_data_row:eq(0) .o_model_field_selector").toHaveCount(1);

    await contains(".o_data_row:eq(1) .o_data_cell[name=name]").click();
    expect(".o_data_row:eq(1) .o_data_cell[name=name] .o_select_menu input").toHaveValue("New");
    await contains(".o_data_row:eq(1) .o_data_cell[name=name] .o_select_menu input").click();
    expect(queryAllTexts(".o_select_menu_item")).toEqual(["New", "Archive"]);
    await contains(".o_select_menu_item:contains(Archive)").click();
    expect(".o_data_row:eq(1) .o_data_cell[name=name] .o_select_menu input").toHaveValue("Archive");

    await contains(".o_data_row:eq(2) .o_data_cell[name=name]").click();
    expect(".o_data_row:eq(2) .o_field_widget[name=name] input").toHaveValue("action_check");
    expect(".o_data_row:eq(1) .o_data_cell[name=name]").toHaveText("Archive");
});

test("only the x2many fields are followed to pick the field of a step", async () => {
    Step._records = [{ id: 1, name: "partner_id", res_model: "tuto.order", type: "field" }];
    await mountSteps();
    await contains(".o_data_row .o_data_cell[name=name]").click();
    await contains(".o_data_row .o_model_field_selector").click();
    expect(".o_model_field_selector_popover_item[data-name=line_ids] .o_model_field_selector_popover_item_relation").toHaveCount(1);
    expect(".o_model_field_selector_popover_item[data-name=partner_id] .o_model_field_selector_popover_item_relation").toHaveCount(0);
});
