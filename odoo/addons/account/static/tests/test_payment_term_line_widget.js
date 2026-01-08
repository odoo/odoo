/** @odoo-module **/
import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView , setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module('Widgets', (hooks) => {
    QUnit.module("PaymentTermsLineWidget");
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                account_payment_term: {
                    fields: {
                        line_ids: {
                            string: "Payment Term Lines",
                            type: "one2many",
                            relation: "account_payment_term_line",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            line_ids: [1, 2],
                        },
                    ],
                },
                account_payment_term_line: {
                    fields: {
                        value_amount: { string: "Due", type: "float" },
                    },
                    records: [
                        {
                            id: 1,
                            value_amount: 0,
                        },
                        {
                            id: 2,
                            value_amount: 50,
                        },
                    ],
                },
            }
        };
        setupViewRegistries();
    });

    QUnit.test("records don't get abandoned after clicking globally or on an exisiting record", async (assert) => {
        await makeView({
            type: "form",
            resModel: "account_payment_term",
            resId: 1,
            serverData,
            arch: `
            <form>
                <field name="line_ids" widget="payment_term_line_ids">
                    <tree string="Payment Terms" editable="top">
                        <field name="value_amount"/>

                    </tree>
                </field>
            </form>
            `,
        });
        assert.containsN(target, ".o_data_row", 2);
        // click the add button
        await click(target.querySelector(".o_field_x2many_list_row_add > a"));
        // make sure the new record is added
        assert.containsN(target, ".o_data_row", 3);
        // global click
        await click(target.querySelector(".o_form_view"));
        // make sure the new record is still there
        assert.containsN(target, ".o_data_row", 3);
        // click the add button again
        await click(target.querySelector(".o_field_x2many_list_row_add > a"));
        // make sure the new record is added
        assert.containsN(target, ".o_data_row", 4);
        // click on an existing record
        await click(target.querySelector(".o_data_row .o_data_cell"));
        // make sure the new record is still there
        assert.containsN(target, ".o_data_row", 4);
    });
});
