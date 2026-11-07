/** @odoo-module **/

import { click, getFixture, editInput } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        bar: { string: "Bar", type: "boolean" },
                        partner_type_id: {
                            string: "Partner Type",
                            type: "many2one",
                            relation: "partner_type"
                        },
                    },
                    records: [
                        { id: 1, name: "A", bar: false, partner_type_id: 1 },
                        { id: 2, name: "B", bar: true, partner_type_id: 1 },
                        { id: 3, name: "C", bar: true, partner_type_id: 1 },
                    ],
                },
                partner_type: {
                    fields: {
                        partner_ids: {
                            string: "Partners",
                            type: "one2many",
                            relation: "partner",
                            relation_field: "partner_type_id"
                        },
                        foo: { string: "Foo", type: "boolean" },
                    },
                    records: [
                        { id: 1, foo: false, partner_ids: [1] }
                    ]
                }
            },
        };

        setupViewRegistries();
    });

    QUnit.module("ListBooleanToggleLoadField");

    QUnit.test("one2many boolean_toggle_load widget saves on change", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner_type",
            serverData,
            arch: `
                <form>
                <field name="partner_ids">
                    <tree editable="top">
                        <field name="name"/>
                        <field name="bar" widget="boolean_toggle_load"/>
                    </tree>
                </field>
            </form>`,
        });

        await click(target, ".o_field_x2many_list_row_add>a");
        await editInput(target, '.o_field_char input', "D");

        await click(target, ".o_field_x2many_list_row_add>a");
        await editInput(target, '.o_field_char input', "E");

        await click(
            target.querySelectorAll('.o_data_row input[type="checkbox"]')[1]
        );

        assert.containsOnce(
            target,
            '[data-tooltip="E"]',
            "Toggling the boolean should trigger a save, and it should not remove any records that were added before the toggle."
        );
    });
});
