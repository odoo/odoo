/* @odoo-module */

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let makeViewParams;

QUnit.module("Sale Project Milestone Form View", (hooks) => {
    hooks.beforeEach(async () => {
        setupViewRegistries();
        makeViewParams = {
            type: "form",
            resModel: "project.milestone",
            serverData: {
                models: {
                    "project.milestone": {
                        fields: {
                            id: { string: "Id", type: "integer" },
                            product_uom_qty: { string: "Quantity", type: "integer" },
                            quantity_percentage: { string: "Percentage", type: "integer" },
                        },
                        records: [
                            { id: 1, product_uom_qty: -1, quantity_percentage: -25 },
                            { id: 2, product_uom_qty: 5, quantity_percentage: 125 },
                            { id: 3, product_uom_qty: 2, quantity_percentage: 0 },
                        ]
                    },
                },
            },
            arch: `
                <form>
                    <field name="product_uom_qty" decoration-danger="quantity_percentage &lt; 0 or 1 &lt; quantity_percentage"/>
                    <field name="quantity_percentage" decoration-danger="quantity_percentage &lt; 0 or 1 &lt; quantity_percentage"/>
                </form>
            `
        };
    });

    QUnit.test("Quantities have text-danger if quantity < 0", async function (assert) {
        makeViewParams.resId = 1;
        await makeView(makeViewParams);
        assert.hasClass($("#quantity_percentage_0").parent(), "text-danger");
        assert.hasClass($("#product_uom_qty_0").parent(), "text-danger");
    });

    QUnit.test("Quantities have text-danger if quantity > 100", async function (assert) {
        makeViewParams.resId = 2;
        await makeView(makeViewParams);
        assert.hasClass($("#quantity_percentage_0").parent(), "text-danger");
        assert.hasClass($("#product_uom_qty_0").parent(), "text-danger");
    });

    QUnit.test("Quantities don't have text-danger if quantity >= 0", async function (assert) {
        makeViewParams.resId = 3;
        await makeView(makeViewParams);
        assert.notOk($("#quantity_percentage_0").parent().hasClass('text-danger'));
        assert.notOk($("#product_uom_qty_0").parent().hasClass('text-danger'));
    });
});
