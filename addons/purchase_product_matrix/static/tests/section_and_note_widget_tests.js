odoo.define('purchase_product_matrix.section_and_note_widget_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var createView = testUtils.createView;

function getGrid(product) {
    return JSON.stringify({
        header: [{name: product.name}, {name: "M"}, {name: "L"}],
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
}

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
                    grid_product_tmpl_id: {string: "Grid Product", type: 'many2one', relation: 'product'},
                },
                onchanges: {
                    grid_product_tmpl_id: (obj) => {
                        const product = this.data.product.records.find((p) => {
                            return p.id === obj.grid_product_tmpl_id;
                        });
                        obj.grid = product ? getGrid(product) : false;
                    },
                    grid: () => {},
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
    },
}, function () {
    QUnit.test('can configure a product with the matrix', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'purchase_order',
            data: this.data,
            arch: `<form>
                    <field name="grid" invisible="1"/>
                    <field name="grid_product_tmpl_id" invisible="1"/>
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
            ' A configurable product M L Men Women ');

        // select 2 M-Men and 3 L-Women
        await testUtils.fields.editInput($matrix.find('.o_matrix_input[ptav_ids="10,13"]'), '2');
        await testUtils.fields.editInput($matrix.find('.o_matrix_input[ptav_ids="11,14"]'), '3');
        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));

        form.destroy();
    });

    QUnit.test('can open the matrix twice with 2 different products', async function (assert) {
        assert.expect(5);

        this.data.product.records.push({ id: 101, name: "Product A" });
        this.data.product.records.push({ id: 102, name: "Product B" });

        const form = await createView({
            View: FormView,
            model: 'purchase_order',
            data: this.data,
            arch: `<form>
                    <field name="grid" invisible="1"/>
                    <field name="grid_product_tmpl_id" invisible="1"/>
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
                        product_template_id: 102,
                    }));
                }
                if (args.method === 'get_single_product_variant') {
                    return Promise.resolve({mode: 'matrix'});
                }
                return this._super.apply(this, arguments);
            },
        });

        // open the matrix with "Product A" and close it
        await testUtils.dom.click('.o_field_x2many_list_row_add a');
        await testUtils.fields.many2one.searchAndClickItem("product_template_id", {item: 'Product A'});

        assert.containsOnce(document.body, '.modal .o_product_variant_matrix');
        let $matrix = $('.modal .o_product_variant_matrix');
        assert.strictEqual($matrix.text().replace(/[\n\r\s\u00a0]+/g, ' '),
            ' Product A M L Men Women ');

        await testUtils.dom.click($('.modal .modal-footer .btn-secondary')); // close

        // re-open the matrix with "Product B"
        await testUtils.dom.click('.o_field_x2many_list_row_add a');
        await testUtils.fields.many2one.searchAndClickItem("product_template_id", {item: 'Product B'});

        assert.containsOnce(document.body, '.modal .o_product_variant_matrix');
        $matrix = $('.modal .o_product_variant_matrix');
        assert.strictEqual($matrix.text().replace(/[\n\r\s\u00a0]+/g, ' '),
            ' Product B M L Men Women ');

        // select 2 M-Men and 3 L-Women
        await testUtils.fields.editInput($matrix.find('.o_matrix_input[ptav_ids="10,13"]'), '2');
        await testUtils.fields.editInput($matrix.find('.o_matrix_input[ptav_ids="11,14"]'), '3');
        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));

        form.destroy();
    });

    QUnit.test('_onTemplateChange is executed after product template quick create', async function (assert) {
        assert.expect(1);

        let created_product_template;

        const form = await createView({
            View: FormView,
            model: 'purchase_order',
            data: this.data,
            arch: `<form>
                    <field name="order_line_ids" widget="section_and_note_one2many">
                        <tree editable="bottom">
                            <field name="product_template_id" widget="matrix_configurator"/>
                        </tree>
                    </field>
                </form>`,
            async mockRPC(route, args) {
                if (route === '/web/dataset/call_kw/product.template/get_single_product_variant') {
                    assert.strictEqual(args.args[0], created_product_template[0]);
                }

                const result = await this._super(...arguments);
                if (args.method === 'name_create') {
                    created_product_template = result;
                }
                return result;
            },
        });

        await testUtils.dom.click('.o_field_x2many_list_row_add a');
        await testUtils.fields.many2one.searchAndClickItem("product_template_id", {search: 'new product'});

        form.destroy();
    });
});
});
