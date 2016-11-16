odoo.define('product.tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require("web.test_utils");

var createView = testUtils.createView;

QUnit.module('product', {
    beforeEach: function () {
        this.data = {
            'product.product': {
                fields: {
                    id: {string: "ID", type: "integer"},
                    weight: {string: "Weight", type: "float"},
                    volume: {string: "Volume", type: "float"},
                },
                records: [{
                    id: 1,
                    weight: 1.11111111111,
                    volume: 10,
                }],
            },
        };
    },
}, function () {
    QUnit.module('My what ? (client action)');

    QUnit.test("edit form view rendering", function (assert) {
        assert.expect(5);

        var form = createView({
            View: FormView,
            model: 'product.product',
            data: this.data,
            res_id: 1,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="weight" widget="weight"/>' +
                            '<field name="volume" widget="volume"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            viewOptions: {mode: 'edit'},
            session: {
                weight_uom: {digits: [69, 2], symbol: 'kg/3', factor: 3, position: 'after'},
                volume_uom: {digits: [69, 2], symbol: 'L*3', factor: 0.33333, position: 'after'},
            },
        });

        assert.strictEqual(form.$('.o_field_measure').length, 2,
            "there should be 2 measure fields");
        assert.strictEqual(form.$('.o_field_measure[name="weight"] > span').text(), 'kg/3',
            "weight widget label not correct");
        assert.strictEqual(form.$('.o_field_measure[name="volume"] > span').text(), 'L*3',
            "volume widget label not correct");

        assert.strictEqual(form.$('.o_field_measure[name="weight"] > input').val(), "3.33",
            "weight widget not converting properly");
        assert.strictEqual(form.$('.o_field_measure[name="volume"] > input').val(), "3.33",
            "volume widget not converting properly");

        form.destroy();
    });
});
});
