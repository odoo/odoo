/** @odoo-module **/

import { click, editInput, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("CountedQuantityWidget", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                'stock.quant': {
                    fields: {
                        quantity: { string: "Quantity", type: "float" },
                        inventory_quantity: { string: "Counted quantity", type: "float" },
                        inventory_quantity_set: { string: "Inventory quantity set", type: "boolean" },
                        inventory_diff_quantity: { string: "Difference", type: "float" },
                    },
                    records: [
                        { id: 1, quantity: 50},
                    ],
                    onchanges: {
                        inventory_quantity: (quant) => {
                            quant.inventory_diff_quantity = quant.inventory_quantity - quant.quantity;
                        },

                    }
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.test("Test changing the inventory quantity with the widget", async function (assert) {
        await makeView({
            type: "list",
            serverData,
            resModel: "stock.quant",
            arch: `<list editable="bottom">
                        <field name="quantity"/>
                        <field name="inventory_quantity" widget="counted_quantity_widget"/>
                        <field name="inventory_quantity_set"/>
                        <field name="inventory_diff_quantity"/>
                   </list>
                `,
        });

        await click(target, "td.o_counted_quantity_widget_cell");
        let input = document.activeElement;
        await editInput(input, null, "23");
        await click(target, "td[name=inventory_diff_quantity]");

        assert.equal(
            target.querySelector("td[name=inventory_diff_quantity] div input").value,
            -27
        );
        assert.strictEqual(
            target.querySelector("td[name=inventory_quantity_set] div input").value,
            "on"
        );

        await click(target, "td.o_counted_quantity_widget_cell");
        input = document.activeElement;
        await editInput(input, null, "40.5");
        await click(target, "td[name=inventory_diff_quantity]");

        assert.equal(
            target.querySelector("td[name=inventory_diff_quantity] div input").value,
            -9.5
        );

    });

    QUnit.test("Test setting the inventory quantity to its default value of 0", async function (assert) {
        await makeView({
            type: "list",
            serverData,
            resModel: "stock.quant",
            arch: `<list editable="bottom">
                        <field name="quantity"/>
                        <field name="inventory_quantity" widget="counted_quantity_widget"/>
                        <field name="inventory_quantity_set"/>
                        <field name="inventory_diff_quantity"/>
                   </list>
                `,
        });

        await click(target, "td.o_counted_quantity_widget_cell");
        let input = document.activeElement;
        await editInput(input, null, "0");
        await click(target, "td[name=inventory_diff_quantity]");

        assert.equal(
            target.querySelector("td[name=inventory_diff_quantity] div input").value,
            -50
        );
    });
});
