/** @odoo-module **/

import { click, getFixture } from "@web/../tests/helpers/utils";
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
                        bar: { string: "Bar", type: "boolean" },
                        partner_type_id: {
                            string: "Partner Type",
                            type: "many2one",
                            relation: "partner_type"
                        },
                    },
                    records: [
                        { id: 1, bar: false, partner_type_id: 1 },
                        { id: 2, bar: true, partner_type_id: 1 },
                        { id: 3, bar: true, partner_type_id: 1 },
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
            arch:`
            <form>
                <field name="partner_ids">
                    <list editable="top">
                        <field name="bar" widget="boolean_toggle_load"/>
                    </list>
                </field>
            </form>`,
            mockRPC(route, { args, method }) {
                if (method === "web_save" && args[1].bar !== undefined) {
                    assert.step(args[1].bar.toString());
                }
            },
        });

        //Set the field up
        await click(target, ".o_field_x2many_list_row_add>a");
        await click(target, ".o_form_button_save");

        //Verify double toggle
        await click(target, ".o_boolean_toggle");
        await click(target, ".o_boolean_toggle");
        assert.verifySteps(["true", "false"], "Toggling the boolean should trigger the save.");
    });
});
