import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Quant extends models.Model {
    quantity = fields.Float();
    inventory_quantity = fields.Float({
        string: "Counted quantity",
        onChange: (quant) => {
            quant.inventory_diff_quantity = quant.inventory_quantity - quant.quantity;
        },
    });
    inventory_quantity_set = fields.Boolean({
        string: "Inventory quantity set",
    });
    inventory_diff_quantity = fields.Float({ string: "Difference" });

    _records = [{ id: 1, quantity: 50 }];
}
defineModels([Quant]);
defineMailModels();

test("Test changing the inventory quantity with the widget", async function () {
    await mountView({
        type: "list",
        resModel: "quant",
        arch: `<list editable="bottom">
                        <field name="quantity"/>
                        <field name="inventory_quantity" widget="counted_quantity_widget"/>
                        <field name="inventory_quantity_set"/>
                        <field name="inventory_diff_quantity"/>
                   </list>
                `,
    });

    await contains("td.o_counted_quantity_widget_cell").click();
    await contains("td.o_counted_quantity_widget_cell input").edit("23");
    await contains("td[name=inventory_diff_quantity]").click();

    expect("td[name=inventory_diff_quantity] div input").toHaveValue(-27);
    expect("td[name=inventory_quantity_set] div input").toBeChecked();

    await contains("td.o_counted_quantity_widget_cell").click();
    await contains("td.o_counted_quantity_widget_cell input").edit("40.5");
    await contains("td[name=inventory_diff_quantity]").click();

    expect("td[name=inventory_diff_quantity] div input").toHaveValue(-9.5);
});

test("Test setting the inventory quantity to its default value of 0", async function () {
    await mountView({
        type: "list",
        resModel: "quant",
        arch: `<list editable="bottom">
                        <field name="quantity"/>
                        <field name="inventory_quantity" widget="counted_quantity_widget"/>
                        <field name="inventory_quantity_set"/>
                        <field name="inventory_diff_quantity"/>
                   </list>
                `,
    });

    await contains("td.o_counted_quantity_widget_cell").click();
    await contains("td.o_counted_quantity_widget_cell input").edit("0");
    await contains("td[name=inventory_diff_quantity]").click();

    expect("td[name=inventory_diff_quantity] div input").toHaveValue(-50);
});

class MockStockMove extends models.Model {
    _name = "stock.move";

    forecast_availability = fields.Float();
    product_qty = fields.Float();
    forecast_expected_date = fields.Date();
    date_deadline = fields.Date();
    state = fields.Selection({
        selection: [
            ["draft", "Draft"],
            ["assigned", "Confirmed"],
        ],
    });

    _records = [
        {
            id: 1,
            forecast_availability: 5,
            product_qty: 10,
            state: "draft",
        },
        {
            id: 2,
            forecast_availability: -1,
            product_qty: 10,
            state: "draft",
        },
    ];
}
defineModels([MockStockMove]);

test("Test that forecast_availability should be Available if availability is greater or equal to 0", async function () {
    await mountView({
        type: "form",
        resModel: "stock.move",
        resId: 1,
        arch: `
            <form>
                <field name="forecast_availability" widget="forecast_widget"/>
                <field name="product_qty" invisible="1"/>
            </form>`,
    });
    expect("div[name='forecast_availability'] span.badge").toHaveText("Available");
});

test("Test that forecast_availability should be 'Not Available' if availability is smaller than 0", async function () {
    await mountView({
        type: "form",
        resModel: "stock.move",
        resId: 2,
        arch: `
            <form>
                <field name="forecast_availability" widget="forecast_widget"/>
            </form>`,
    });
    expect("div[name='forecast_availability'] span.badge").toHaveText("Not Available");
});
