odoo.define('web.basic_model_tests', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var testUtils = require('web.test_utils');

var createModel = testUtils.createModel;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: {string: "STRING", type: 'char'},
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
            product: {
                fields: {
                    name: {string: "Product Name", type: "char"}
                },
                records: [
                    {id: 37, display_name: "xphone"},
                    {id: 41, display_name: "xpad"}
                ]
            },
            partner_type: {
                fields: {
                    display_name: {string: "Partner Type", type: "char"}
                },
                records: [
                    {id: 12, display_name: "gold"},
                    {id: 14, display_name: "silver"},
                    {id: 15, display_name: "bronze"}
                ]
            },
        };

        // add related fields to category.
        this.data.partner.fields.category.relatedFields =
            $.extend(true, {}, this.data.partner_type.fields);
        this.params = {
            res_id: 2,
            modelName: 'partner',
            fields: this.data.partner.fields,
        };
    }
}, function () {
    QUnit.module('BasicModel');

    QUnit.test('simple functionality', function (assert) {
        assert.expect(6);

        this.params.fieldNames = ['foo'];

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

    QUnit.test('notify change with many2one', function (assert) {
        assert.expect(2);

        this.params.fieldNames = ['foo', 'qux'];

        var model = createModel({
            Model: BasicModel,
            data: this.data,
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.qux, false, "qux field should be false");
            model.notifyChanges(resultID, {qux: {id: 1, display_name: "hello"}});

            record = model.get(resultID);
            assert.strictEqual(record.data.qux.data.id, 1, "qux field should be 1");
        });
        model.destroy();
    });

    QUnit.test('write on a many2one', function (assert) {
        assert.expect(4);
        var self = this;

        this.params.fieldNames = ['product_id'];

        var rpcCount = 0;

        var model = createModel({
            Model: BasicModel,
            data: this.data,
            mockRPC: function (route, args) {
                rpcCount++;
                return this._super(route, args);
            },
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id.data.display_name, 'xpad',
                "should be initialized with correct value");

            model.notifyChanges(resultID, {product_id: {id: 37, display_name: 'xphone'}});

            record = model.get(resultID);
            assert.strictEqual(record.data.product_id.data.display_name, 'xphone',
                "should be changed with correct value");

            model.save(resultID);

            assert.strictEqual(self.data.partner.records[1].product_id, 37,
                "should have really saved the data");
            assert.strictEqual(rpcCount, 3, "should have done 3 rpc: 1 read, 1 write, 1 read");
        });
        model.destroy();
    });

    QUnit.test('basic onchange', function (assert) {
        assert.expect(5);

        this.data.partner.onchanges.foo = function (obj) {
            obj.bar = obj.foo.length;
        };

        this.params.fieldNames = ['foo', 'bar'];
        this.params.context = {hello: 'world'};

        var model = createModel({
            Model: BasicModel,
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    var context = args.args[4];
                    assert.deepEqual(context, {hello: 'world'},
                        "context should be sent by the onchange");
                }
                return this._super(route, args);
            },
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'gnap', "foo field is properly initialized");
            assert.strictEqual(record.data.bar, 2, "bar field is properly initialized");

            model.notifyChanges(resultID, {foo: 'mary poppins'});

            record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'mary poppins', "onchange has been applied");
            assert.strictEqual(record.data.bar, 12, "onchange has been applied");
        });
        model.destroy();
    });

    QUnit.test('onchange with a many2one', function (assert) {
        assert.expect(5);

        this.data.partner.onchanges.product_id = function (obj) {
            if (obj.product_id === 37) {
                obj.foo = "space lollipop";
            }
        };

        this.params.fieldNames = ['foo', 'product_id'];

        var rpcCount = 0;

        var model = createModel({
            Model: BasicModel,
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    assert.strictEqual(args.args[2], "product_id",
                        "should send the only changed field as a string, not a list");
                }
                rpcCount++;
                return this._super(route, args);
            },
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'gnap', "foo field is properly initialized");
            assert.strictEqual(record.data.product_id.data.id, 41, "product_id field is properly initialized");

            model.notifyChanges(resultID, {product_id: {id: 37, display_name: 'xphone'}});

            record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'space lollipop', "onchange has been applied");
            assert.strictEqual(rpcCount, 2, "should have done 2 rpc: 1 read and 1 onchange");
        });
        model.destroy();
    });

    QUnit.test('notifyChange on a many2one, without display_name', function (assert) {
        assert.expect(3);

        this.params.fieldNames = ['product_id'];

        var model = createModel({
            Model: BasicModel,
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'name_get') {
                    assert.strictEqual(args.model, 'product');
                }
                return this._super(route, args);
            },
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id.data.display_name, 'xpad',
                "product_id field is set to xpad");

            model.notifyChanges(resultID, {product_id: {id: 37}});

            record = model.get(resultID);
            assert.strictEqual(record.data.product_id.data.display_name, 'xphone',
                "display_name should have been fetched");
        });
        model.destroy();
    });

    QUnit.test('onchange on a char with an unchanged many2one', function (assert) {
        assert.expect(2);

        this.data.partner.onchanges.foo = function (obj) {
            obj.foo = obj.foo + " alligator";
        };

        this.params.fieldNames = ['foo', 'product_id'];

        var model = createModel({
            Model: BasicModel,
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    assert.strictEqual(args.args[1].product_id, 41, "should send correct value");
                }
                return this._super(route, args);
            },
        });

        model.load(this.params).then(function (resultID) {
            model.notifyChanges(resultID, {foo: 'cookie'});
            var record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'cookie alligator', "onchange has been applied");
        });
        model.destroy();
    });

    QUnit.test('onchange on a char with another many2one not set to a value', function (assert) {
        assert.expect(2);
        this.data.partner.records[0].product_id = false;
        this.data.partner.onchanges.foo = function (obj) {
            obj.foo = obj.foo + " alligator";
        };

        this.params.fieldNames = ['foo', 'product_id'];
        this.params.res_id = 1;

        var model = createModel({
            Model: BasicModel,
            data: this.data,
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id, false, "product_id is not set");

            model.notifyChanges(resultID, {foo: 'cookie'});
            record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'cookie alligator', "onchange has been applied");
        });
        model.destroy();
    });

    QUnit.test('can get a many2many', function (assert) {
        assert.expect(3);

        this.params.res_id = 1;
        this.params.fieldNames = ['category'];

        var model = createModel({
            Model: BasicModel,
            data: this.data,
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.category.data[0].res_id, 12,
                "should have loaded many2omany res_ids");
            assert.strictEqual(record.data.category.data[0].data.display_name, "gold",
                "should have loaded many2omany display_name");
            record = model.get(resultID, {raw: true});
            assert.deepEqual(record.data.category, [12],
                "with option raw, category should only return ids");
        });
        model.destroy();
    });

    QUnit.test('can fetch a list', function (assert) {
        assert.expect(4);

        this.params.fieldNames = ['foo'];
        this.params.domain = [];
        this.params.groupedBy = [];
        this.params.res_id = undefined;

        var rpcCount = 0;
        var model = createModel({
            Model: BasicModel,
            data: this.data,
            mockRPC: function (route, args) {
                rpcCount++;
                return this._super(route, args);
            },
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);

            assert.strictEqual(record.type, 'list', "record fetched should be a list");
            assert.strictEqual(record.data.length, 2, "should have fetched 2 records");
            assert.strictEqual(record.data[0].data.foo, 'blip', "first record should have 'blip' in foo field");
            assert.strictEqual(rpcCount, 1, "should have done 1 rpc (searchread)");
        });
        model.destroy();
    });

    QUnit.test('fetch x2manys in list, with not too many rpcs', function (assert) {
        assert.expect(2);

        this.data.partner.records[0].category = [12, 15];
        this.data.partner.records[1].category = [12, 14];

        this.params.fieldNames = ['category'];
        this.params.domain = [];
        this.params.groupedBy = [];
        this.params.res_id = undefined;

        var rpcCount = 0;
        var model = createModel({
            Model: BasicModel,
            data: this.data,
            mockRPC: function (route, args) {
                rpcCount++;
                return this._super(route, args);
            },
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);

            assert.strictEqual(record.data[0].data.category.data.length, 2,
                "first record should have 2 categories loaded");
            assert.strictEqual(rpcCount, 2, "should have done 2 rpc (searchread and read category)");
        });
        model.destroy();
    });

    QUnit.test('can make a default_record, no onchange', function (assert) {
        assert.expect(3);

        this.params.fieldNames = ['product_id', 'category', 'product_ids'];
        this.params.res_id = undefined;
        this.params.context = {};

        var model = createModel({
            Model: BasicModel,
            data: this.data,
        });

        model.makeDefaultRecord('partner', this.params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id, false, "m2o default value should be false");
            assert.deepEqual(record.data.product_ids.data, [], "o2m default should be []");
            assert.deepEqual(record.data.category.data, [], "m2m default should be []");
        });
        model.destroy();
    });

    QUnit.test('default_record, with onchange on many2one', function (assert) {
        assert.expect(1);

        // the onchange is done by the mockRPC because we want to return a value
        // of 'false', which does not work with the mockserver mockOnChange method.
        this.data.partner.onchanges.product_id = true;

        this.params.fieldNames = ['product_id'];
        this.params.res_id = undefined;
        this.params.context = {};

        var model = createModel({
            Model: BasicModel,
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    return $.when({value: { product_id: false }});
                }
                return this._super(route, args);
            },
        });

        model.makeDefaultRecord('partner', this.params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id, false, "m2o default value should be false");
        });
        model.destroy();
    });

    QUnit.test('default record: batch namegets on same model and res_id', function (assert) {
        assert.expect(3);

        var rpcCount = 0;
        var fields = this.data.partner.fields;
        fields.other_product_id = _.extend({}, fields.product_id);
        fields.product_id.default = 37;
        fields.other_product_id.default = 41;

        var model = createModel({
            Model: BasicModel,
            data: this.data,
            mockRPC: function (route, args) {
                rpcCount++;
                return this._super(route, args);
            },
        });

        var params = {
            context: {},
            fieldNames: ['other_product_id', 'product_id'],
            fields: fields,
        };

        model.makeDefaultRecord('partner', params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id.data.display_name, "xphone",
                "should have fetched correct name");
            assert.strictEqual(record.data.other_product_id.data.display_name, "xpad",
                "should have fetched correct name");
            assert.strictEqual(rpcCount, 2, "should have done 2 rpcs: default_get and 1 name_get");
        });
        model.destroy();
    });

    QUnit.test('undoing a change makes the record not dirty', function (assert) {
        assert.expect(4);

        this.params.fieldNames = ['foo'];

        var model = createModel({
            Model: BasicModel,
            data: this.data,
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.foo, "gnap", "foo field should properly be set");
            assert.ok(!model.isDirty(resultID), "record should not be dirty");
            model.notifyChanges(resultID, {foo: "hello"});
            assert.ok(model.isDirty(resultID), "record should be dirty");
            model.notifyChanges(resultID, {foo: "gnap"});
            assert.ok(!model.isDirty(resultID), "record should not be dirty");
        });
        model.destroy();
    });

    QUnit.test('isDirty works correctly on list made empty', function (assert) {
        assert.expect(3);

        this.params.fieldNames = ['category'];
        this.params.res_id = 1;

        var model = createModel({
            Model: BasicModel,
            data: this.data,
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);
            var category_value = record.data.category;
            assert.ok(_.isObject(category_value), "category field should have been fetched");
            assert.strictEqual(category_value.data.length, 1, "category field should contain one record");
            model.notifyChanges(resultID, {category: {
                operation: 'REMOVE',
                id: category_value.data[0].id
            }});
            assert.ok(model.isDirty(resultID), "record should be considered dirty");
        });
        model.destroy();
    });

    QUnit.test('can duplicate a record', function (assert) {
        assert.expect(4);

        this.params.fieldNames = ['foo'];

        var model = createModel({
            Model: BasicModel,
            data: this.data,
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.display_name, "second partner",
                "record should have correct display name");
            assert.strictEqual(record.data.foo, "gnap", "foo should be set to correct value");
            model.duplicateRecord(resultID).then(function (duplicateID) {
                var duplicate = model.get(duplicateID);
                assert.strictEqual(duplicate.data.display_name, "second partner (copy)",
                    "record should have been duplicated");
                assert.strictEqual(duplicate.data.foo, "gnap", "foo should be set to correct value");
            });
        });
        model.destroy();
    });

    QUnit.test('record with many2one set to some value, then set it to none', function (assert) {
        assert.expect(3);

        this.params.fieldNames = ['product_id'];

        var self = this;
        var model = createModel({
            Model: BasicModel,
            data: this.data,
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id.data.display_name, 'xpad', "product_id should be set");
            model.notifyChanges(resultID, {product_id: false});

            record = model.get(resultID);
            assert.strictEqual(record.data.product_id, false, "product_id should not be set");

            model.save(resultID);

            assert.strictEqual(self.data.partner.records[1].product_id, false,
                "should have saved the new product_id value");
        });
        model.destroy();
    });

    QUnit.test('groups stay open when reloading', function (assert) {
        assert.expect(5);

        this.params.fieldNames = ['foo'];
        this.params.domain = [];
        this.params.groupedBy = ['product_id'];
        this.params.res_id = undefined;

        var model = createModel({
            Model: BasicModel,
            data: this.data,
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.length, 2, "should have 2 groups");
            var groupID = record.data[0].id;
            model.toggleGroup(groupID);

            record = model.get(resultID);
            assert.ok(record.data[0].isOpen, "first group should be open");
            assert.strictEqual(record.data[0].data.length, 1, "first group should have one record");

            model.reload(resultID);
            record = model.get(resultID);
            assert.ok(record.data[0].isOpen, "first group should still be open");
            assert.strictEqual(record.data[0].data.length, 1, "first group should still have one record");
        });
        model.destroy();
    });

    QUnit.test('create record, then save', function (assert) {
        assert.expect(4);

        this.params.fieldNames = ['product_ids'];

        var id;
        var model = createModel({
            Model: BasicModel,
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    // has to be done before the call to _super
                    assert.notOk('product_ids' in args.args[0], "should not have any value");
                    assert.notOk('category' in args.args[0], "should not have other fields");
                }
                var result = this._super(route, args);
                if (args.method === 'create') {
                    result.then(function (res) {
                        id = res;
                    });
                }
                return result;
            },
        });

        model.makeDefaultRecord('partner', this.params).then(function (resultID) {
            var record = model.get(resultID);
            model.save(record.id, {reload: false});
            record = model.get(resultID);
            assert.strictEqual(record.res_id, id, "should have correct id from server");
            assert.strictEqual(record.data.id, id, "should have correct id from server");
        });
        model.destroy();
    });


    QUnit.test('write commands on a one2many', function (assert) {
        assert.expect(4);

        this.data.partner.records[1].product_ids = [37];

        this.params.fieldNames = ['product_ids'];

        var model = createModel({
            Model: BasicModel,
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[0], [2], "should write on res_id = 2");
                    var commands = args.args[1].product_ids;
                    assert.deepEqual(commands[0], [4, 37, false], "first command should be a 4");
                    // TO DO: uncomment next line
                    // assert.strictEqual(commands[1], [0, false, {name: "toy"}], "second command should be a 0");
                    assert.strictEqual(commands[1][0], 0, "second command should be a 0");
                }
                return this._super(route, args);
            },
        });

        model.load(this.params).then(function (resultID) {
            var record = model.get(resultID, {raw: true});
            assert.deepEqual(record.data.product_ids, [37], "should have correct initial value");

            var relatedRecordID = model.makeRecord('product', [{
                    name: 'name',
                    string: "Product Name",
                    type: "char",
                    value: "xpod"
                }
            ]);

            model.notifyChanges(record.id, {
                product_ids: {operation: "ADD", id: relatedRecordID}
            });

            model.save(record.id);
        });
        model.destroy();
    });

    QUnit.test('onchange with a one2many on a new record', function (assert) {
        assert.expect(4);

        this.data.partner.fields.total.default = 50;
        this.data.partner.onchanges.product_ids = function (obj) {
            obj.total += 100;
        };

        this.params.fieldNames = ['total', 'product_ids'];

        var model = createModel({
            Model: BasicModel,
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'onchange' && args.args[1].total === 150) {
                    assert.deepEqual(args.args[1].product_ids, [[0, false, {name: "xpod"}]],
                        "Should have sent the create command in the onchange");
                }
                return this._super(route, args);
            },
        });

        model.makeDefaultRecord('partner', this.params).then(function (resultID) {

            var record = model.get(resultID);
            assert.strictEqual(record.data.product_ids.data.length, 0,
                "one2many should start with a list of length 0");

            var relatedRecordID = model.makeRecord('product', [{
                    name: 'name',
                    string: "Product Name",
                    type: "char",
                    value: "xpod"
                }
            ]);
            model.notifyChanges(resultID, {
                product_ids: {operation: "ADD", id: relatedRecordID}
            });

            record = model.get(resultID);
            assert.strictEqual(record.data.product_ids.data.length, 1,
                "one2many should be a list of length 1");
            assert.strictEqual(record.data.product_ids.data[0].data.name, "xpod",
                "one2many should have correct data");
        });
        model.destroy();
    });

    QUnit.test('dates are properly loaded and parsed (record)', function (assert) {
        assert.expect(2);

        var model = createModel({
            Model: BasicModel,
            data: this.data,
        });

        var params = {
            fieldNames: ['date'],
            fields: this.data.partner.fields,
            modelName: 'partner',
            res_id: 1,
        };

        model.load(params).then(function (resultID) {
            var record = model.get(resultID);
            assert.ok(record.data.date instanceof moment,
                "fetched date field should have been formatted");
        });

        params.res_id = 2;

        model.load(params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.date, false,
                "unset date field should be false");
        });
        model.destroy();
    });

    QUnit.test('dates are properly loaded and parsed (list)', function (assert) {
        assert.expect(2);

        var model = createModel({
            Model: BasicModel,
            data: this.data,
        });

        var params = {
            fieldNames: ['date'],
            fields: this.data.partner.fields,
            modelName: 'partner',
            type: 'list',
        };

        model.load(params).then(function (resultID) {
            var record = model.get(resultID);
            var firstRecord = record.data[0];
            var secondRecord = record.data[1];
            assert.ok(firstRecord.data.date instanceof moment,
                "fetched date field should have been formatted");
            assert.strictEqual(secondRecord.data.date, false,
                "if date is not set, it should be false");
        });
        model.destroy();
    });

    QUnit.test('dates are properly loaded and parsed (default_get)', function (assert) {
        assert.expect(1);

        var model = createModel({
            Model: BasicModel,
            data: this.data,
        });

        var params = {
            fieldNames: ['date'],
            fields: this.data.partner.fields,
            modelName: 'partner',
        };

        model.makeDefaultRecord('partner', params).then(function (resultID) {
            var record = model.get(resultID);
            assert.strictEqual(record.data.date, false, "date default value should be false");
        });
        model.destroy();
    });


});});
