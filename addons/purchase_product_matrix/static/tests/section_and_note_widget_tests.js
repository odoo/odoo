odoo.define('purchase_product_matrix.section_and_note_widget_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var createView = testUtils.createView;

QUnit.module('section_and_note: purchase_product_matrix', {
    beforeEach: function () {
        this.data = {
            purchase_order: {
                fields: {
                    order_line_ids: {
                        string: "Lines",
                        type: 'one2many',
                        relation: 'order_line',
                        relation_field: 'order_id',
                    },
                    grid: {string: "Grid", type: 'char'},
                },
            },
            order_line: {
                fields: {
                    order_id: {string: "Invoice", type: 'many2one', relation: 'invoice'},
                    product_template_id: {string: "Product", type: 'many2one', relation: 'product'},
                },
            },
            product: {
                fields: {
                    name: {string: "Name", type: 'char'},
                },
                records: [
                    {id: 1, name: 'A configurable product'},
                ],
            },
        };

        this.grid = JSON.stringify({
            header: [{name: "My Company Tshirt (GRID)"}, {name: "M"}, {name: "L"}],
            matrix: [[
                {name: "Men"},
                {ptav_ids: [10, 13], qty: 0, is_possible_combination: true},
                {ptav_ids: [11, 13], qty: 0, is_possible_combination: true},
            ], [
                {name: "Women"},
                {ptav_ids: [10, 14], qty: 0, is_possible_combination: true},
                {ptav_ids: [11, 14], qty: 0, is_possible_combination: true},
            ]],
        });
    },
}, function () {
    QUnit.test('can configure a product with the matrix', async function (assert) {
        assert.expect(4);

        this.data.purchase_order.onchanges = {
            order_line_ids: obj => {
                obj.grid = this.grid;
            },
            grid: () => {},
        };
        var form = await createView({
            View: FormView,
            model: 'purchase_order',
            data: this.data,
            arch: `<form>
                    <field name="grid" invisible="1"/>
                    <field name="order_line_ids" widget="section_and_note_one2many">
                        <tree editable="bottom">
                            <field name="product_template_id" widget="matrix_configurator"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC: function (route, args) {
                if (args.method === 'onchange' && args.args[2] === 'grid') {
                    // should trigger an onchange on the grid field and let the
                    // business logic create rows according to the matrix content
                    assert.deepEqual(args.args[1].grid, JSON.stringify({
                        changes: [{qty: 2, ptav_ids: [10, 13]}, {qty: 3, ptav_ids: [11, 14]}],
                        product_template_id: 1,
                    }));
                }
                if (args.method === 'get_single_product_variant') {
                    assert.strictEqual(args.args[0], 1);
                    return Promise.resolve({mode: 'matrix'});
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click('.o_field_x2many_list_row_add a');
        await testUtils.fields.many2one.searchAndClickItem("product_template_id", {item: 'configurable'});

        assert.containsOnce(document.body, '.modal .o_product_variant_matrix');
        const $matrix = $('.modal .o_product_variant_matrix');
        assert.strictEqual($matrix.text().replace(/[\n\r\s\u00a0]+/g, ' '),
            ' My Company Tshirt (GRID) M L Men Women ');

        // select 2 M-Men and 3 L-Women
        await testUtils.fields.editInput($matrix.find('.o_matrix_input[ptav_ids="10,13"]'), '2');
        await testUtils.fields.editInput($matrix.find('.o_matrix_input[ptav_ids="11,14"]'), '3');
        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));

        form.destroy();
    });
});
});
