odoo.define("web.relational_fields_mobile_tests", function (require) {
"use strict";

const FormView = require("web.FormView");
const testUtils = require("web.test_utils");

QUnit.module("fields", {}, function () {
    QUnit.module("relational_fields", {
        beforeEach() {
            this.data = {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        p: {string: "one2many field", type: "one2many", relation: "partner", relation_field: "trululu"},
                        trululu: {string: "Trululu", type: "many2one", relation: "partner"},
                    },
                    records: [{
                        id: 1,
                        display_name: "first record",
                        p: [2, 4],
                        trululu: 4,
                    }, {
                        id: 2,
                        display_name: "second record",
                        p: [],
                        trululu: 1,
                    }, {
                        id: 4,
                        display_name: "aaa",
                    }],
                },
            };
        },
    }, function () {
        QUnit.module("FieldOne2Many");

        QUnit.test("one2many on mobile: display list if present without kanban view", async function (assert) {
            assert.expect(2);

            const form = await testUtils.createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: `
                    <form>
                        <field name="p">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                        </field>
                    </form>
                `,
                res_id: 1,
            });

            await testUtils.form.clickEdit(form);
            assert.containsOnce(form, ".o_field_x2many_list",
                "should display one2many's list");
            assert.containsN(form, ".o_field_x2many_list .o_data_row", 2,
                "should display 2 records in one2many's list");

            form.destroy();
        });
    });
});
});
