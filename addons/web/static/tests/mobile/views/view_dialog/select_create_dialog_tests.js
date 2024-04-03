/** @odoo-module */

import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

QUnit.module("ViewDialogs", (hooks) => {
    let serverData;
    let target;

    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                product: {
                    fields: {
                        id: { type: "integer" },
                        name: {},
                    },
                    records: [
                        {
                            id: 111,
                            name: "product_cable_management_box",
                        },
                    ],
                },
                sale_order_line: {
                    fields: {
                        id: { type: "integer" },
                        product_id: {
                            string: "product_id",
                            type: "many2one",
                            relation: "product",
                        },
                        linked_sale_order_line: {
                            string: "linked_sale_order_line",
                            type: "many2many",
                            relation: "sale_order_line",
                        },
                    },
                },
            },
            views: {
                "product,false,kanban": `
                    <kanban><templates><t t-name="kanban-box">
                        <div class="oe_kanban_global_click">
                            <field name="id"/>
                            <field name="name"/>
                        </div>
                    </t></templates></kanban>
                `,
                "sale_order_line,false,kanban": `
                    <kanban><templates><t t-name="kanban-box">
                        <div class="oe_kanban_global_click">
                            <field name="id"/>
                        </div>
                    </t></templates></kanban>
                `,
                "product,false,search": "<search></search>",
            },
        };
        setupViewRegistries();
    });

    QUnit.module("SelectCreateDialog - Mobile");

    QUnit.test("SelectCreateDialog: clear selection in mobile", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "form",
            resModel: "sale_order_line",
            serverData,
            arch: `
                <form>
                    <field name="product_id"/>
                    <field name="linked_sale_order_line" widget="many2many_tags"/>
                </form>`,
            async mockRPC(route, args) {
                if (args.method === "create" && args.model === "sale_order_line") {
                    const { product_id: selectedId } = args.args[0];
                    assert.strictEqual(selectedId, false, `there should be no product selected`);
                }
            },
        });
        const clearBtnSelector = ".btn.o_clear_button";

        await click(target, '.o_field_widget[name="linked_sale_order_line"] input');
        let modal = target.querySelector(".modal-dialog.modal-lg");
        assert.containsNone(modal, clearBtnSelector, "there shouldn't be a Clear button");
        await click(modal, ".o_form_button_cancel");

        // Select a product
        await click(target, '.o_field_widget[name="product_id"] input');
        modal = target.querySelector(".modal-dialog.modal-lg");
        await click(modal, ".o_kanban_record:nth-child(1)");

        // Remove the product
        await click(target, '.o_field_widget[name="product_id"] input');
        modal = target.querySelector(".modal-dialog.modal-lg");
        assert.containsOnce(modal, clearBtnSelector, "there should be a Clear button");
        await click(modal, clearBtnSelector);

        await click(target, ".o_form_button_save");
    });

    QUnit.test("SelectCreateDialog: selection_mode should be true", async function (assert) {
        assert.expect(3);

        serverData.views["product,false,kanban"] = `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                         <div class="o_primary" t-if="!selection_mode">
                            <a type="object" name="some_action">
                                <field name="name"/>
                            </a>
                         </div>
                         <div class="o_primary" t-if="selection_mode">
                             <field name="name"/>
                         </div>
                    </t>
                </templates>
            </kanban>`;

        await makeView({
            type: "form",
            resModel: "sale_order_line",
            serverData,
            arch: `
                <form>
                    <field name="product_id"/>
                    <field name="linked_sale_order_line" widget="many2many_tags"/>
                </form>`,
            async mockRPC(route, args) {
                if (args.method === "create" && args.model === "sale_order_line") {
                    const { product_id: selectedId } = args.args[0];
                    assert.strictEqual(selectedId, 111, `the product should be selected`);
                }
                if (args.method === "some_action") {
                    assert.step("action should not be called");
                }
            },
        });

        await click(target, '.o_field_widget[name="product_id"] input');
        await click(target, ".modal-dialog.modal-lg .o_kanban_record:nth-child(1) .o_primary span");
        assert.containsNone(target, ".modal-dialog.modal-lg");
        await click(target, ".o_form_button_save");
        assert.verifySteps([]);
    });
});
