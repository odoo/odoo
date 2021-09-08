odoo.define('sale.product_configurator_tests', function (require) {
    "use strict";

    const FormView = require('web.FormView');
    const testUtils = require('web.test_utils');

    const createView = testUtils.createView;

    QUnit.module('product_configurator', {
        beforeEach: function () {
            this.data = {
                order: {
                    fields: {
                        line_ids: {
                            string: "Lines",
                            type: 'one2many',
                            relation: 'line',
                            relation_field: 'order_id'
                        },
                    },
                    records: [
                        {id: 1, line_ids: [1, 2]},
                    ],
                },
                line: {
                    fields: {
                        product_id: {
                            string: "Product",
                            type: 'many2one',
                            relation: 'product',
                        },
                        order_id: {
                            string: "Order",
                            type: 'many2one',
                            relation: 'order'
                        },
                        sequence: {
                            string: "Sequence",
                            type: 'integer',
                        },
                    },
                    records: [
                        {id: 1, sequence: 4, product_id: 3, order_id: 1},
                        {id: 2, sequence: 14, product_id: 4, order_id: 1},
                    ]
                },
                product: {
                    fields: {
                        name: {
                            string: "Name",
                            type: 'char',
                        },
                    },
                    records: [
                        {id: 3, name: "Chair"},
                        {id: 4, name: "Table"},
                    ],
                },
            };
        },
    }, function () {
        QUnit.test('drag and drop rows containing product_configurator many2one', async function (assert) {
            assert.expect(4);

            const form = await createView({
                View: FormView,
                model: 'order',
                data: this.data,
                arch: `
                    <form>
                        <field name="line_ids"/>
                    </form>`,
                archs: {
                    'line,false,list': `
                        <tree editable="bottom">
                            <field name="sequence" widget="handle"/>
                            <field name="product_id" widget="product_configurator"/>
                        </tree>`,
                },
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            assert.containsN(form, '.o_data_row', 2);
            assert.strictEqual(form.$('.o_data_row').text(), 'ChairTable');
            assert.containsN(form, '.o_data_row .o_row_handle', 2);

            // move first row below second
            const $firstHandle = form.$('.o_data_row:nth(0) .o_row_handle');
            const $secondHandle = form.$('.o_data_row:nth(1) .o_row_handle');
            await testUtils.dom.dragAndDrop($firstHandle, $secondHandle);

            assert.strictEqual(form.$('.o_data_row').text(), 'TableChair');

            form.destroy();
        });

        QUnit.test('product_configurator many2one with readonly modifier inside editable list view', async function (assert) {
            assert.expect(5);

            const form = await createView({
                View: FormView,
                model: 'order',
                data: this.data,
                arch: `
                    <form>
                        <field name="line_ids"/>
                    </form>`,
                archs: {
                    'line,false,list': `
                        <tree editable="bottom">
                            <field name="sequence"/>
                            <field name="product_id" widget="product_configurator" attrs="{'readonly': [('sequence', '>', 4)]}"/>
                        </tree>`,
                },
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            assert.containsN(form, '.o_data_row', 2);

            await testUtils.dom.click(form.$('.o_field_one2many .o_list_table .o_data_cell:first'));
            assert.containsOnce(form, '.o_field_one2many .o_data_row .o_product_configurator_cell input.ui-autocomplete-input',
                "editable row should have editable many2one");

            await testUtils.dom.click(form.$('.o_field_one2many .o_list_table .o_data_row:eq(1) .o_data_cell:first'));
            assert.containsNone(form, '.o_field_one2many .o_data_row:eq(1) .o_product_configurator_cell input.ui-autocomplete-input',
                "editable row should not have editable many2one");
            assert.containsOnce(form, '.o_field_one2many .o_data_row:eq(1) .o_product_configurator_cell a.o_form_uri',
                "editable row should have readonly many2one with link");
            assert.hasAttrValue(form.$('.o_field_one2many .o_data_row:eq(1) .o_product_configurator_cell a.o_form_uri'), 'href', "#id=4&model=product",
                "href should contain id and model");

            form.destroy();
        });
    });
});
