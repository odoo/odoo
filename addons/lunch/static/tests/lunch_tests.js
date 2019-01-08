odoo.define('lunch.tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('lunch', {
    beforeEach: function () {
        this.data = {
            order: {
                fields: {
                    previous_order_widget: {type: 'text'},
                    order_line_ids: {type: 'many2many', relation: 'order_line'}
                },
                records: [{
                    id: 1,
                    name: 'coucou',
                }, {
                    id: 2,
                    name: 'coucou',
                }, {
                    id: 11,
                }],
            },
            order_line: {
                fields: {
                    product_id: {type: 'many2one', relation: 'product'},
                    note: {type: 'text'},
                    price: {type: 'float'},
                },
            },
            supplier: {
                fields: {},
                records: [{
                    id: 1,
                    display_name: "Coin Gourmant",
                }, {
                    id: 2,
                    display_name: "Pizza Inn",
                }]
            },
            product: {
                fields: {},
                records: [{
                    id: 1,
                    name: 'Pizza Margherita',
                }],
            }
        };
    },
}, function () {

    QUnit.test("empty previous_order widget", function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="previous_order_widget" widget="previous_order"/>' +
                        '<field name="order_line_ids"/>' +
                    '</sheet>' +
                  '</form>',
            data: this.data,
            model: 'order',
            archs: {
                "order_line,false,list": '<tree string="Orders">' +
                        '<field name="product_id"/>' +
                        '<field name="note"/>' +
                        '<field name="price"/>' +
                    '</tree>',
            },
        });

        var widgetText = form.$('.o_field_widget[name="previous_order_widget"]').text();
        assert.ok(widgetText.indexOf('This is the first time you order a meal') !== -1,
            "the widget should display its no content text");
        assert.containsNone(form, '.o_lunch_vignette',
            "there should be no vignette");

        form.destroy();
    });

    QUnit.test("add an order line with previous_order widget", function (assert) {
        assert.expect(4);

        var form = createView({
            View: FormView,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="previous_order_widget" widget="previous_order"/>' +
                        '<field name="order_line_ids"/>' +
                    '</sheet>' +
                  '</form>',
            data: this.data,
            model: 'order',
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    return $.when({
                        previous_order_widget: '{' +
                            '"8": {' +
                                '"note": "coucou",' +
                                '"line_id": 8,' +
                                '"digits": [69, 2],' +
                                '"product_id": 1,' +
                                '"currency": "$",' +
                                '"supplier": "Pizza Inn",' +
                                '"position": "before",' +
                                '"price": 6.9,' +
                                '"product_name": "Pizza Margherita"' +
                            '}' +
                        '}'
                    });
                }
                return this._super.apply(this, arguments);
            },
            archs: {
                "order_line,false,list": '<tree string="Orders">' +
                        '<field name="product_id"/>' +
                        '<field name="note"/>' +
                        '<field name="price"/>' +
                    '</tree>',
            },
        });

        assert.containsNone(form, '.o_list_view tr.o_data_row',
            "there should be no row in the one2many list");

        assert.containsOnce(form, '.o_lunch_vignette',
            "there should be a vignette");

        // add an order
        testUtils.dom.click(form.$('.o_lunch_vignette .o_add_button'));

        assert.containsOnce(form, '.o_list_view tr.o_data_row',
            "there should be one new row in the one2many list");
        assert.strictEqual(form.$('.o_list_view tr.o_data_row').text(), "Pizza Margheritacoucou6.90",
            "the line should contain the correct data");

        form.destroy();
    });
});
});
