odoo.define('mrp.mrp_tests', function (require) {
"use strict";

var MrpState = require('mrp.mrp');

var testUtils = require('web.test_utils');

var createModel = testUtils.createModel;

QUnit.module('mrp', {
	beforeEach: function () {
    this.data = {
            partner: {
                fields: {
                    display_name: {string: "NAME", type: 'char'},
                    total: {string: "Total", type: 'integer'},
                    foo: {string: "Foo", type: 'char'},
                    bar: {string: "Bar", type: 'integer'},
                    qux: {string: "Qux", type: 'many2one', relation: 'partner'},
                    product_id: {string: "Favorite product", type: 'many2one', relation: 'product'},
                    product_ids: {string: "Favorite products", type: 'one2many', relation: 'product'},
                    category: {string: "Category M2M", type: 'many2many', relation: 'partner_type'},
                    date: {string: "Date Field", type: 'date'},
                },
                records: [
                    {id: 1, foo: 'blip', bar: 1, product_id: 37, category: [12], display_name: "first partner", date: "2017-01-25"},
                    {id: 2, foo: 'gnap', bar: 2, product_id: 41, display_name: "second partner"},
                ],
                onchanges: {},
            },
            partner_type: {
                fields: {
                    display_name: {string: "Partner Type", type: "char"},
                    date: {string: "Date Field", type: 'date'},
                },
                records: [
                    {id: 12, display_name: "gold", date: "2017-01-25"},
                    {id: 14, display_name: "silver"},
                    {id: 15, display_name: "bronze"}
                ]
            },
            product: {
            	fields: {
            		field1: { string: "Name", type: 'char', state: },
            		field2: { string: "Price", type: 'integer'},
            	},
            	records: {
            		{ id: 1, field1: "Product1" },
            		{ id: 30, field1: "Product2" },
            		{ id: 3, field1: "Product3", date: "2017-04-21" },
            	},
            }
        };
    }, function () {
    QUnit.module('MRPFields');

    QUnit.test('simple functionality', function (assert) {
    	assert.expect(1);

    	assert.strictEqual();
    	his.params.fieldNames = ['foo'];

        var model = createModel({
            Model: BasicModel,
            data: this.data,
        });

        assert.strictEqual(model.get(1), null, "should return null for non existing key");

        model.load(this.params).then(function (resultID) {
            // it is a string, because it is used as a key in an object
            assert.strictEqual(typeof resultID, 'string', "result should be a valid id");

            var record = model.get(resultID);
            assert.strictEqual(record.res_id, 2, "res_id read should be the same as asked");
            assert.strictEqual(record.type, 'record', "should be of type 'record'");
            assert.strictEqual(record.data.foo, "gnap", "should correctly read value");
            assert.strictEqual(record.data.bar, undefined, "should not fetch the field 'bar'");
        });
        model.destroy();
    });
	}

});