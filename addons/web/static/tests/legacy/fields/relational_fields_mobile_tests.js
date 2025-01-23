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
        QUnit.test("in mobiler kanban view with no data should display no content helper", async function (assert) {
            assert.expect(3);
            this.data.partner.records = [];
            var form = await testUtils.createView({
                View: FormView,
                arch:
                    '<form>' +
                        '<sheet>' +
                            '<field name="trululu"/>' +
                        '</sheet>' +
                    '</form>',
                archs: {
                    'partner,false,kanban': '<kanban>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div class="oe_kanban_global_click"><field name="display_name"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
                    'partner,false,search': '<search></search>',
                },
                data: this.data,
                model: 'partner',
                config: {device: {isMobile: true}},
                viewOptions: {mode: 'edit'},
            });

            const $input = form.$('.o_field_many2one input');

            await testUtils.dom.click($input);
            await testUtils.nextTick();
            await testUtils.nextTick();
            await testUtils.nextTick();
            await testUtils.nextTick();

            const $modal = $('.o_modal_full .modal-lg');
            assert.equal($modal.length, 1, 'there should be one modal opened in full screen');
            assert.containsOnce($modal, '.o_kanban_view',
                'kanban view should be open in SelectCreateDialog');
            assert.containsOnce($modal, '.o_nocontent_help',
                'kanban view should have no content helper');
            form.destroy();
        });
    });
});
});
