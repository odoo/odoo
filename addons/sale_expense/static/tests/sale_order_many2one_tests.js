odoo.define('sale_expense.field_many_to_one_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;


QUnit.module('sale_expense', {
    beforeEach: function () {
        this.data = {
            'hr.expense': {
                fields: {
                    name: { string: "Description", type: "char" },
                    sale_order_id: { string: "Reinvoice Customer", type: 'many2one', relation: 'sale.order' },
                },
                records: []
            },
            'sale.order': {
                fields: {
                    name: { string: "Name", type: "char" },
                },
                records: [{
                    id: 1,
                    name: "SO1",
                }, {
                    id: 2,
                    name: "SO2",
                }, {
                    id: 3,
                    name: "SO3"
                }, {
                    id: 4,
                    name: "SO4"
                }, {
                    id: 5,
                    name: "SO5"
                }, {
                    id: 6,
                    name: "SO6"
                }, {
                    id: 7,
                    name: "SO7"
                }, {
                    id: 8,
                    name: "SO8"
                }, {
                    id: 9,
                    name: "SO9"
                }]
            },
        };
    },
}, function () {
    QUnit.test('sale order many2one without search more option', async function (assert) {
        assert.expect(3);
        var form = await createView({
            View: FormView,
            model: 'hr.expense',
            data: this.data,
            arch:
                '<form string="Expense">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="sale_order_id" widget="sale_order_many2one"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>'
        });
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        await testUtils.fields.many2one.clickOpenDropdown('sale_order_id');
        assert.containsN($dropdown, 'li:not(.o_m2o_dropdown_option)', 9);
        assert.containsNone($dropdown, 'li.o_m2o_dropdown_option');
        assert.containsNone($dropdown, 'li.o_m2o_dropdown_option:contains("Search More...")', "Should not display the 'Search More... option'");
        form.destroy();
    });
});
});
