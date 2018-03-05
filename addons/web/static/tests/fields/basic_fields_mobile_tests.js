odoo.define('web.basic_fields_tests', function (require) {
"use strict";

var core = require('web.core');
var FormView = require('web.FormView');
var session = require('web.session');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;
var _t = core._t;

QUnit.module('fields', {}, function () {

QUnit.module('basic_fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: {string: "Displayed name", type: "char", searchable: true},
                    int_field: {string: "int_field", type: "integer", sortable: true, searchable: true},
                    qux: {string: "Qux", type: "float", digits: [16,1], searchable: true},
                    currency_id: {string: "Currency", type: "many2one", relation: "currency", searchable: true},
                },
                records: [{
                    id: 1,
                    int_field: 10,
                    qux: 0.44444,
                }, {
                    id: 2,
                    display_name: "second record",
                    int_field: 0,
                    currency_id: 2,
                    qux: 0,
                }, {
                    id: 4,
                    display_name: "aaa",
                    int_field: false,
                    qux: false,
                },
                {id: 3, bar: true, foo: "gnap", int_field: 80, qux: -3.89859, m2o: 1, m2m: []},
                {id: 5, bar: false, foo: "blop", int_field: -4, qux: 9.1, m2o: 1, m2m: [1], currency_id: 1}],
                onchanges: {},
            },
            currency: {
                fields: {
                    symbol: {string: "Currency Sumbol", type: "char", searchable: true},
                    position: {string: "Currency Position", type: "char", searchable: true},
                },
                records: [{
                    id: 1,
                    display_name: "$",
                    symbol: "$",
                    position: "before",
                }, {
                    id: 2,
                    display_name: "€",
                    symbol: "€",
                    position: "after",
                }]
            },
        };
    }
}, function () {

    QUnit.module('FieldInteger');

    QUnit.test('integer field in editable mode', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="int_field"/></form>',
            res_id: 4,
        });
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_field_widget').attr('type'), "tel",
            'Type of integer field should be tel.');

        form.destroy();
    });

    QUnit.module('FieldFloat');

    QUnit.test('float field in editable mode', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="qux"/></form>',
            res_id: 1,
        });
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_field_widget').attr('type'), "tel",
            'Type of float field should be tel.');

        form.destroy();
    });

    QUnit.module('FieldMonetary');

    QUnit.test('Monetary field in editable mode', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<field name="qux" widget="monetary"/>' +
                        '<field name="currency_id" invisible="1"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 5,
            session: {
                currencies: _.indexBy(this.data.currency.records, 'id'),
            },
        });
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_field_monetary input').attr('type'), "tel",
            'Type of Monetary field should be tel.');

        form.destroy();
    });
});
});
});
