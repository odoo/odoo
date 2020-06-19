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
                            type: 'number',
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
    });
});
