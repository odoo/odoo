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
