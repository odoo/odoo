/** @odoo-module **/

import {
    getFixture,
    patchWithCleanup,
    addRow,
    editInput,
    triggerHotkey,
    nextTick
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { browser } from "@web/core/browser/browser";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                'sale.order': {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        order_line: {
                            string: "order lines",
                            type: "one2many",
                            relation: "sale.order.line",
                            relation_field: "order_id",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            order_line: [],
                        },
                    ],
                    onchanges: {},
                },
                'sale.order.line': {
                    fields: {
                        product_template_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product.template",
                        },
                    },
                    records: [
                    ],
                },
                'product.template': {
                    fields: {
                        display_name: { string: "Partner Type", type: "char" },
                        name: { string: "Partner Type", type: "char" },
                    },
                    records: [
                        { id: 12, display_name: "desk" },
                    ],
                    methods:  {
                        get_single_product_variant() {
                            return Promise.resolve({product_id: 12});
                        }
                    }
                },
                user: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        partner_ids: {
                            string: "one2many partners field",
                            type: "one2many",
                            relation: "partner",
                            relation_field: "user_id",
                        },
                    },
                    records: [
                    ],
                },
            },
        };

        setupViewRegistries();

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
    });

    QUnit.module("Sale product field");

    QUnit.test("pressing tab with incomplete text will create a product", async function (assert) {

        await makeView({
            type: "form",
            resModel: "sale.order",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="order_line">
                            <tree editable="bottom" >
                                <field name="product_template_id" widget="sol_product_many2one" />
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
            }
        });

        // add a line and enter new product name
        await addRow(target, ".o_field_x2many_list");
        await editInput(target, "[name='product_template_id'] input", "new product");
        await triggerHotkey("tab");
        await nextTick();
        assert.verifySteps([
            "get_views",
            "onchange",
            "onchange",
            "name_search",
            "name_create",
            "get_single_product_variant",
        ]);
    });

});
