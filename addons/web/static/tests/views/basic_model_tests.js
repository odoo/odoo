odoo.define('web.basic_model_tests', function (require) {
    "use strict";

    var BasicModel = require('web.BasicModel');
    var FormView = require('web.FormView');
    var testUtils = require('web.test_utils');

    var createModel = testUtils.createModel;
    var createView = testUtils.createView;

    QUnit.module('Views', {
        beforeEach: function () {
            this.data = {
                partner: {
                    fields: {
                        display_name: { string: "STRING", type: 'char' },
                        // the following 2 fields must remain in that order to check that
                        // active has priority over x_active despite the order
                        x_active: { string: "Custom Active", type: 'boolean', default: true},
                        active: {string: "Active", type: 'boolean', default: true},
                        total: { string: "Total", type: 'integer' },
                        foo: { string: "Foo", type: 'char' },
                        bar: { string: "Bar", type: 'integer' },
                        qux: { string: "Qux", type: 'many2one', relation: 'partner' },
                        product_id: { string: "Favorite product", type: 'many2one', relation: 'product' },
                        product_ids: { string: "Favorite products", type: 'one2many', relation: 'product' },
                        category: { string: "Category M2M", type: 'many2many', relation: 'partner_type' },
                        date: { string: "Date Field", type: 'date' },
                        reference: { string: "Reference Field", type: 'reference', selection: [["product", "Product"], ["partner_type", "Partner Type"], ["partner", "Partner"]] },
                    },
                    records: [
                        { id: 1, foo: 'blip', bar: 1, product_id: 37, category: [12], display_name: "first partner", date: "2017-01-25" },
                        { id: 2, foo: 'gnap', bar: 2, product_id: 41, display_name: "second partner" },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        display_name: { string: "Product Display Name", type: "char" },
                        name: { string: "Product Name", type: "char" },
                        category: { string: "Category M2M", type: 'many2many', relation: 'partner_type' },
                        active: {string: "Active", type: 'boolean', default: true},
                    },
                    records: [
                        { id: 37, display_name: "xphone" },
                        { id: 41, display_name: "xpad" }
                    ]
                },
                partner_type: {
                    fields: {
                        display_name: { string: "Partner Type", type: "char" },
                        date: { string: "Date Field", type: 'date' },
                        x_active: { string: "Custom Active", type: 'boolean', default: true},
                    },
                    records: [
                        { id: 12, display_name: "gold", date: "2017-01-25" },
                        { id: 14, display_name: "silver" },
                        { id: 15, display_name: "bronze" }
                    ]
                },
                partner_title: {
                    fields: {
                        display_name: { string: "Partner Title", type: 'char'},
                    },
                    records: [
                        { id: 42, display_name: "Dr."},
                    ]
                }
            };

            // add related fields to category.
            this.data.partner.fields.category.relatedFields =
                $.extend(true, {}, this.data.partner_type.fields);
            this.params = {
                res_id: 2,
                modelName: 'partner',
                fields: this.data.partner.fields,
            };
        },
    }, function () {
        QUnit.module('BasicModel');

        QUnit.test('context is given when using a resequence', async function (assert) {
            assert.expect(2);
            delete this.params["res_id"];
            this.data.product.fields.sequence = {string: "Sequence", type: "integer"};

            const model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/resequence') {
                        assert.deepEqual(args.context, { active_field: 2 },
                            "context should be correct after a resequence");
                    }
                    else if (args.method === "read") {
                        assert.deepEqual(args.kwargs.context, { active_field: 2 },
                            "context should be correct after a 'read' RPC");
                    }
                    return this._super.apply(this, arguments);
                },
            });
            const params = _.extend(this.params, {
                context: { active_field: 2 },
                groupedBy: ['product_id'],
                fieldNames: ['foo'],
            });
    
            model.load(params)
                .then(function (stateID) {
                    return model.resequence('product', [41, 37], stateID);
                })
                .then(function () {
                    model.destroy();
                });
        });

        QUnit.test('can process x2many commands', async function (assert) {
            assert.expect(6);

            this.data.partner.fields.product_ids.default = [[0, 0, { category: [] }]];

            const form = await createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: `
                    <form>
                        <field name="product_ids"/>
                    </form>
                `,
                archs: {
                    'product,false,list': `
                        <tree>
                            <field name="display_name"/>
                        </tree>
                    `,
                    'product,false,kanban': `
                        <kanban>
                            <templates><t t-name="kanban-box">
                                <div><field name="display_name"/></div>
                            </t></templates>
                        </kanban>
                    `,
                },
                viewOptions: {
                    mode: 'edit',
                },
                mockRPC(route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });

            assert.verifySteps([
                'load_views',
                'onchange',
            ]);
            assert.containsOnce(form, '.o_field_x2many_list', 'should have rendered a x2many list');
            assert.containsOnce(form, '.o_data_row', 'should have added 1 record as default');
            assert.containsOnce(form, '.o_field_x2many_list_row_add', 'should have rendered a x2many add row on list');
            form.destroy();
        });

        QUnit.test('can process x2many commands (with multiple fields)', async function (assert) {
            assert.expect(1);

            this.data.partner.fields.product_ids.default = [[0, 0, { category: [] }]];

            const form = await createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: `
                    <form>
                        <field name="product_ids"/>
                    </form>
                `,
                archs: {
                    'product,false,list': `
                        <tree>
                            <field name="display_name"/>
                            <field name="active"/>
                        </tree>
                    `,
                },
                mockRPC(route, args) {
                    if (args.method === "create") {
                        const product_ids = args.args[0].product_ids;
                        const values = product_ids[0][2];
                        assert.strictEqual(values.active, true, "active field should be set");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            await testUtils.form.clickSave(form);
            form.destroy();
        });

        QUnit.test('can load a record', async function (assert) {
            assert.expect(7);

            this.params.fieldNames = ['foo'];
            this.params.context = { active_field: 2 };

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    assert.deepEqual(args.kwargs.context, {
                        active_field: 2,
                        bin_size: true,
                        someKey: 'some value',
                    }, "should have sent the correct context");
                    return this._super.apply(this, arguments);
                },
                session: {
                    user_context: { someKey: 'some value' },
                }
            });

            assert.strictEqual(model.get(1), null, "should return null for non existing key");

            var resultID = await model.load(this.params);
            // it is a string, because it is used as a key in an object
            assert.strictEqual(typeof resultID, 'string', "result should be a valid id");

            var record = model.get(resultID);
            assert.strictEqual(record.res_id, 2, "res_id read should be the same as asked");
            assert.strictEqual(record.type, 'record', "should be of type 'record'");
            assert.strictEqual(record.data.foo, "gnap", "should correctly read value");
            assert.strictEqual(record.data.bar, undefined, "should not fetch the field 'bar'");
            model.destroy();
        });

        QUnit.test('rejects loading a record with invalid id', async function (assert) {
            assert.expect(1);

            this.params.res_id = 99;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });
            try {
                await model.load(this.params);
            }
            catch (e) {
                assert.ok("load should return a rejected deferred for an invalid id");
            }

            model.destroy();
        });

        QUnit.test('notify change with many2one', async function (assert) {
            assert.expect(2);

            this.params.fieldNames = ['foo', 'qux'];

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.qux, false, "qux field should be false");
            await model.notifyChanges(resultID, { qux: { id: 1, display_name: "hello" } });

            record = model.get(resultID);
            assert.strictEqual(record.data.qux.data.id, 1, "qux field should be 1");
            model.destroy();
        });

        QUnit.test('notify change on many2one: unset and reset same value', async function (assert) {
            assert.expect(3);

            this.data.partner.records[1].qux = 1;

            this.params.fieldNames = ['qux'];
            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.qux.data.id, 1, "qux value should be 1");

            await model.notifyChanges(resultID, { qux: false });
            record = model.get(resultID);
            assert.strictEqual(record.data.qux, false, "qux should be unset");

            await model.notifyChanges(resultID, { qux: { id: 1, display_name: 'second_partner' } });
            record = model.get(resultID);
            assert.strictEqual(record.data.qux.data.id, 1, "qux value should be 1 again");
            model.destroy();
        });

        QUnit.test('write on a many2one', async function (assert) {
            assert.expect(4);
            var self = this;

            this.params.fieldNames = ['product_id'];

            var rpcCount = 0;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    rpcCount++;
                    return this._super(route, args);
                },
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id.data.display_name, 'xpad',
                "should be initialized with correct value");

            await model.notifyChanges(resultID, { product_id: { id: 37, display_name: 'xphone' } });

            record = model.get(resultID);
            assert.strictEqual(record.data.product_id.data.display_name, 'xphone',
                "should be changed with correct value");

            await model.save(resultID);

            assert.strictEqual(self.data.partner.records[1].product_id, 37,
                "should have really saved the data");
            assert.strictEqual(rpcCount, 3, "should have done 3 rpc: 1 read, 1 write, 1 read");
            model.destroy();
        });

        QUnit.test('basic onchange', async function (assert) {
            assert.expect(5);

            this.data.partner.fields.foo.onChange = true;
            this.data.partner.onchanges.foo = function (obj) {
                obj.bar = obj.foo.length;
            };

            this.params.fieldNames = ['foo', 'bar'];
            this.params.context = { hello: 'world' };

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    if (args.method === 'onchange') {
                        var context = args.kwargs.context;
                        assert.deepEqual(context, { hello: 'world' },
                            "context should be sent by the onchange");
                    }
                    return this._super(route, args);
                },
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'gnap', "foo field is properly initialized");
            assert.strictEqual(record.data.bar, 2, "bar field is properly initialized");

            await model.notifyChanges(resultID, { foo: 'mary poppins' });

            record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'mary poppins', "onchange has been applied");
            assert.strictEqual(record.data.bar, 12, "onchange has been applied");
            model.destroy();
        });

        QUnit.test('onchange with a many2one', async function (assert) {
            assert.expect(5);

            this.data.partner.fields.product_id.onChange = true;
            this.data.partner.onchanges.product_id = function (obj) {
                if (obj.product_id === 37) {
                    obj.foo = "space lollipop";
                }
            };

            this.params.fieldNames = ['foo', 'product_id'];

            var rpcCount = 0;

            var model = await createModel({
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

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'gnap', "foo field is properly initialized");
            assert.strictEqual(record.data.product_id.data.id, 41, "product_id field is properly initialized");

            await model.notifyChanges(resultID, { product_id: { id: 37, display_name: 'xphone' } });

            record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'space lollipop', "onchange has been applied");
            assert.strictEqual(rpcCount, 2, "should have done 2 rpc: 1 read and 1 onchange");
            model.destroy();
        });

        QUnit.test('onchange on a one2many not in view (fieldNames)', async function (assert) {
            assert.expect(6);

            this.data.partner.fields.foo.onChange = true;
            this.data.partner.onchanges.foo = function (obj) {
                obj.bar = obj.foo.length;
                obj.product_ids = [];
            };

            this.params.fieldNames = ['foo'];

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'gnap', "foo field is properly initialized");
            assert.strictEqual(record.data.bar, undefined, "bar field is not loaded");
            assert.strictEqual(record.data.product_ids, undefined, "product_ids field is not loaded");

            await model.notifyChanges(resultID, { foo: 'mary poppins' });

            record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'mary poppins', "onchange has been applied");
            assert.strictEqual(record.data.bar, 12, "onchange has been applied");
            assert.strictEqual(record.data.product_ids, undefined,
                "onchange on product_ids (one2many) has not been applied");
            model.destroy();
        });

        QUnit.test('notifyChange on a one2many', async function (assert) {
            assert.expect(9);

            this.data.partner.records[1].product_ids = [37];
            this.params.fieldNames = ['product_ids'];

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    if (args.method === 'name_get') {
                        assert.strictEqual(args.model, 'product');
                    }
                    return this._super(route, args);
                },
            });

            var o2mParams = {
                modelName: 'product',
                fields: this.data.product.fields,
                fieldNames: ['display_name'],
            };
            var resultID = await model.load(this.params);
            var newRecordID = await model.load(o2mParams);
            var record = model.get(resultID);
            var x2mListID = record.data.product_ids.id;

            assert.strictEqual(record.data.product_ids.count, 1,
                "there should be one record in the relation");

            // trigger a 'ADD' command
            await model.notifyChanges(resultID, { product_ids: { operation: 'ADD', id: newRecordID } });

            assert.deepEqual(model.localData[x2mListID]._changes, [{
                operation: 'ADD', id: newRecordID,
            }], "_changes should be correct");
            record = model.get(resultID);
            assert.strictEqual(record.data.product_ids.count, 2,
                "there should be two records in the relation");

            // trigger a 'UPDATE' command
            await model.notifyChanges(resultID, { product_ids: { operation: 'UPDATE', id: newRecordID } });

            assert.deepEqual(model.localData[x2mListID]._changes, [{
                operation: 'ADD', id: newRecordID,
            }, {
                operation: 'UPDATE', id: newRecordID,
            }], "_changes should be correct");
            record = model.get(resultID);
            assert.strictEqual(record.data.product_ids.count, 2,
                "there should be two records in the relation");

            // trigger a 'DELETE' command on the existing record
            var existingRecordID = record.data.product_ids.data[0].id;
            await model.notifyChanges(resultID, { product_ids: { operation: 'DELETE', ids: [existingRecordID] } });

            assert.deepEqual(model.localData[x2mListID]._changes, [{
                operation: 'ADD', id: newRecordID,
            }, {
                operation: 'UPDATE', id: newRecordID,
            }, {
                operation: 'DELETE', id: existingRecordID,
            }],
                "_changes should be correct");
            record = model.get(resultID);
            assert.strictEqual(record.data.product_ids.count, 1,
                "there should be one record in the relation");

            // trigger a 'DELETE' command on the new record
            await model.notifyChanges(resultID, { product_ids: { operation: 'DELETE', ids: [newRecordID] } });

            assert.deepEqual(model.localData[x2mListID]._changes, [{
                operation: 'DELETE', id: existingRecordID,
            }], "_changes should be correct");
            record = model.get(resultID);
            assert.strictEqual(record.data.product_ids.count, 0,
                "there should be no record in the relation");

            model.destroy();
        });

        QUnit.test('notifyChange on a many2one, without display_name', async function (assert) {
            assert.expect(3);

            this.params.fieldNames = ['product_id'];

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    if (args.method === 'name_get') {
                        assert.strictEqual(args.model, 'product');
                    }
                    return this._super(route, args);
                },
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id.data.display_name, 'xpad',
                "product_id field is set to xpad");

            await model.notifyChanges(resultID, { product_id: { id: 37 } });

            record = model.get(resultID);
            assert.strictEqual(record.data.product_id.data.display_name, 'xphone',
                "display_name should have been fetched");
            model.destroy();
        });

        QUnit.test('onchange on a char with an unchanged many2one', async function (assert) {
            assert.expect(2);

            this.data.partner.fields.foo.onChange = true;
            this.data.partner.onchanges.foo = function (obj) {
                obj.foo = obj.foo + " alligator";
            };

            this.params.fieldNames = ['foo', 'product_id'];

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    if (args.method === 'onchange') {
                        assert.strictEqual(args.args[1].product_id, 41, "should send correct value");
                    }
                    return this._super(route, args);
                },
            });

            var resultID = await model.load(this.params);
            await model.notifyChanges(resultID, { foo: 'cookie' });
            var record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'cookie alligator', "onchange has been applied");
            model.destroy();
        });

        QUnit.test('onchange on a char with another many2one not set to a value', async function (assert) {
            assert.expect(2);
            this.data.partner.records[0].product_id = false;
            this.data.partner.fields.foo.onChange = true;
            this.data.partner.onchanges.foo = function (obj) {
                obj.foo = obj.foo + " alligator";
            };

            this.params.fieldNames = ['foo', 'product_id'];
            this.params.res_id = 1;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id, false, "product_id is not set");

            await model.notifyChanges(resultID, { foo: 'cookie' });
            record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'cookie alligator', "onchange has been applied");
            model.destroy();
        });

        QUnit.test('can get a many2many', async function (assert) {
            assert.expect(3);

            this.params.res_id = 1;
            this.params.fieldsInfo = {
                default: {
                    category: {
                        fieldsInfo: { default: { display_name: {} } },
                        relatedFields: { display_name: { type: "char" } },
                        viewType: 'default',
                    },
                },
            };

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.category.data[0].res_id, 12,
                "should have loaded many2many res_ids");
            assert.strictEqual(record.data.category.data[0].data.display_name, "gold",
                "should have loaded many2many display_name");
            record = model.get(resultID, { raw: true });
            assert.deepEqual(record.data.category, [12],
                "with option raw, category should only return ids");
            model.destroy();
        });

        QUnit.test('can use command add and get many2many value with date field', async function (assert) {
            assert.expect(2);

            this.params.fieldsInfo = {
                default: {
                    category: {
                        fieldsInfo: { default: { date: {} } },
                        relatedFields: { date: { type: "date" } },
                        viewType: 'default',
                    },
                },
            };

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var changes = {
                category: { operation: 'ADD_M2M', ids: [{ id: 12 }] }
            };
            await model.notifyChanges(resultID, changes);
            var record = model.get(resultID);
            assert.strictEqual(record.data.category.data.length, 1, "should have added one category");
            assert.strictEqual(record.data.category.data[0].data.date instanceof moment,
                true, "should have a date parsed in a moment object");
            model.destroy();
        });

        QUnit.test('many2many with ADD_M2M command and context with parent key', async function (assert) {
            assert.expect(1);

            this.data.partner_type.fields.some_char = { type: "char" };
            this.params.fieldsInfo = {
                default: {
                    category: {
                        fieldsInfo: { default: { some_char: { context: "{'a': parent.foo}" } } },
                        relatedFields: { some_char: { type: "char" } },
                        viewType: 'default',
                    },
                    foo: {},
                },
            };

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var changes = {
                category: { operation: 'ADD_M2M', ids: [{ id: 12 }] }
            };
            await model.notifyChanges(resultID, changes);
            var record = model.get(resultID);
            var categoryRecord = record.data.category.data[0];
            assert.deepEqual(categoryRecord.getContext({ fieldName: 'some_char' }), { a: 'gnap' },
                "should properly evaluate context");
            model.destroy();
        });

        QUnit.test('can fetch a list', async function (assert) {
            assert.expect(4);

            this.params.fieldNames = ['foo'];
            this.params.domain = [];
            this.params.groupedBy = [];
            this.params.res_id = undefined;
            this.params.context = { active_field: 2 };

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    assert.strictEqual(args.context.active_field, 2,
                        "should have sent the correct context");
                    return this._super(route, args);
                },
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);

            assert.strictEqual(record.type, 'list', "record fetched should be a list");
            assert.strictEqual(record.data.length, 2, "should have fetched 2 records");
            assert.strictEqual(record.data[0].data.foo, 'blip', "first record should have 'blip' in foo field");
            model.destroy();
        });

        QUnit.test('fetch x2manys in list, with not too many rpcs', async function (assert) {
            assert.expect(3);

            this.data.partner.records[0].category = [12, 15];
            this.data.partner.records[1].category = [12, 14];

            this.params.fieldNames = ['category'];
            this.params.domain = [];
            this.params.groupedBy = [];
            this.params.res_id = undefined;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    assert.step(route);
                    return this._super(route, args);
                },
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);

            assert.strictEqual(record.data[0].data.category.data.length, 2,
                "first record should have 2 categories loaded");
            assert.verifySteps(["/web/dataset/search_read"],
                "should have done 2 rpc (searchread and read category)");
            model.destroy();
        });

        QUnit.test('can make a default_record with the help of onchange', async function (assert) {
            assert.expect(5);

            this.params.context = {};
            this.params.fieldNames = ['product_id', 'category', 'product_ids'];
            this.params.res_id = undefined;
            this.params.type = 'record';

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super(route, args);
                },
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id, false, "m2o default value should be false");
            assert.deepEqual(record.data.product_ids.data, [], "o2m default should be []");
            assert.deepEqual(record.data.category.data, [], "m2m default should be []");

            assert.verifySteps(['onchange']);

            model.destroy();
        });

        QUnit.test('default_get returning a non requested field', async function (assert) {
            // 'default_get' returns a default value for the fields given in
            // arguments. It should not return a value for fields that have not be
            // requested. However, it happens (e.g. res.users), and the webclient
            // should not crash when this situation occurs (the field should simply
            // be ignored).
            assert.expect(2);

            this.params.context = {};
            this.params.fieldNames = ['category'];
            this.params.res_id = undefined;
            this.params.type = 'record';

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    var result = this._super(route, args);
                    if (args.method === 'default_get') {
                        result.product_ids = [[6, 0, [37, 41]]];
                    }
                    return result;
                },
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.ok('category' in record.data,
                "should have processed 'category'");
            assert.notOk('product_ids' in record.data,
                "should have ignored 'product_ids'");

            model.destroy();
        });

        QUnit.test('can make a default_record with default relational values', async function (assert) {
            assert.expect(6);

            this.data.partner.fields.product_id.default = 37;
            this.data.partner.fields.product_ids.default = [
                [0, false, { name: 'xmac' }],
                [0, false, { name: 'xcloud' }]
            ];
            this.data.partner.fields.category.default = [
                [6, false, [12, 14]]
            ];

            this.params.fieldNames = ['product_id', 'category', 'product_ids'];
            this.params.res_id = undefined;
            this.params.type = 'record';
            this.params.fieldsInfo = {
                form: {
                    category: {},
                    product_id: {},
                    product_ids: {
                        fieldsInfo: {
                            default: { name: {} },
                        },
                        relatedFields: this.data.product.fields,
                        viewType: 'default',
                    },
                },
            };
            this.params.viewType = 'form';

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super(route, args);
                },
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.deepEqual(record.data.product_id.data.display_name, 'xphone',
                "m2o default should be xphone");
            assert.deepEqual(record.data.product_ids.data.length,
                2, "o2m default should have two records");
            assert.deepEqual(record.data.product_ids.data[0].data.name,
                'xmac', "first o2m default value should be xmac");
            assert.deepEqual(record.data.category.res_ids, [12, 14],
                "m2m default should be [12, 14]");

            assert.verifySteps(['onchange']);

            model.destroy();
        });

        QUnit.test('default_record, with onchange on many2one', async function (assert) {
            assert.expect(1);

            // the onchange is done by the mockRPC because we want to return a value
            // of 'false', which does not work with the mockserver mockOnChange method.
            this.data.partner.onchanges.product_id = true;

            this.params.context = {};
            this.params.fieldNames = ['product_id'];
            this.params.res_id = undefined;
            this.params.type = 'record';

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    if (args.method === 'onchange') {
                        return Promise.resolve({ value: { product_id: false } });
                    }
                    return this._super(route, args);
                },
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id, false, "m2o default value should be false");
            model.destroy();
        });

        QUnit.test('default record: batch namegets on same model and res_id', async function (assert) {
            assert.expect(3);

            var rpcCount = 0;
            var fields = this.data.partner.fields;
            fields.other_product_id = _.extend({}, fields.product_id);
            fields.product_id.default = 37;
            fields.other_product_id.default = 41;

            var model = await createModel({
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
                modelName: 'partner',
                type: 'record',
            };

            var resultID = await model.load(params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id.data.display_name, "xphone",
                "should have fetched correct name");
            assert.strictEqual(record.data.other_product_id.data.display_name, "xpad",
                "should have fetched correct name");
            assert.strictEqual(rpcCount, 1, "should have done 1 rpc: onchange");
            model.destroy();
        });

        QUnit.test('undoing a change keeps the record dirty', async function (assert) {
            assert.expect(4);

            this.params.fieldNames = ['foo'];

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.foo, "gnap", "foo field should properly be set");
            assert.ok(!model.isDirty(resultID), "record should not be dirty");
            await model.notifyChanges(resultID, { foo: "hello" });
            assert.ok(model.isDirty(resultID), "record should be dirty");
            await model.notifyChanges(resultID, { foo: "gnap" });
            assert.ok(model.isDirty(resultID), "record should be dirty");
            model.destroy();
        });

        QUnit.test('isDirty works correctly on list made empty', async function (assert) {
            assert.expect(3);

            this.params.fieldNames = ['category'];
            this.params.res_id = 1;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            var category_value = record.data.category;
            assert.ok(_.isObject(category_value), "category field should have been fetched");
            assert.strictEqual(category_value.data.length, 1, "category field should contain one record");
            await model.notifyChanges(resultID, {
                category: {
                    operation: 'DELETE',
                    ids: [category_value.data[0].id],
                }
            });
            assert.ok(model.isDirty(resultID), "record should be considered dirty");
            model.destroy();
        });

        QUnit.test('can duplicate a record', async function (assert) {
            assert.expect(4);

            this.params.fieldNames = ['foo'];

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.display_name, "second partner",
                "record should have correct display name");
            assert.strictEqual(record.data.foo, "gnap", "foo should be set to correct value");
            var duplicateID = await model.duplicateRecord(resultID);
            var duplicate = model.get(duplicateID);
            assert.strictEqual(duplicate.data.display_name, "second partner (copy)",
                "record should have been duplicated");
            assert.strictEqual(duplicate.data.foo, "gnap", "foo should be set to correct value");
            model.destroy();
        });

        QUnit.test('record with many2one set to some value, then set it to none', async function (assert) {
            assert.expect(3);

            this.params.fieldNames = ['product_id'];

            var self = this;
            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_id.data.display_name, 'xpad', "product_id should be set");
            await model.notifyChanges(resultID, { product_id: false });

            record = model.get(resultID);
            assert.strictEqual(record.data.product_id, false, "product_id should not be set");

            await model.save(resultID);

            assert.strictEqual(self.data.partner.records[1].product_id, false,
                "should have saved the new product_id value");
            model.destroy();
        });

        QUnit.test('internal state of groups remains when reloading', async function (assert) {
            assert.expect(10);

            this.params.fieldNames = ['foo'];
            this.params.domain = [];
            this.params.limit = 80;
            this.params.groupedBy = ['product_id'];
            this.params.res_id = undefined;

            var filterEnabled = false;
            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    if (args.method === 'web_read_group' && filterEnabled) {
                        // as this is not yet supported by the MockServer, simulates
                        // a read_group that returns empty groups
                        // this is the case for several models (e.g. project.task
                        // grouped by stage_id)
                        return this._super.apply(this, arguments).then(function (result) {
                            // artificially filter out records of first group
                            result.groups[0].product_id_count = 0;
                            return result;
                        });
                    }
                    return this._super.apply(this, arguments);
                },
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.length, 2, "should have 2 groups");
            var groupID = record.data[0].id;
            assert.strictEqual(model.localData[groupID].parentID, resultID,
                "parentID should be correctly set on groups");

            await model.toggleGroup(groupID);

            record = model.get(resultID);
            assert.ok(record.data[0].isOpen, "first group should be open");
            assert.strictEqual(record.data[0].data.length, 1,
                "first group should have one record");
            assert.strictEqual(record.data[0].limit, 80,
                "limit should be 80 by default");

            // change the limit and offset of the first group
            model.localData[record.data[0].id].limit = 10;

            await model.reload(resultID);
            record = model.get(resultID);
            assert.ok(record.data[0].isOpen, "first group should still be open");
            assert.strictEqual(record.data[0].data.length, 1,
                "first group should still have one record");
            assert.strictEqual(record.data[0].limit, 10,
                "new limit should have been kept");

            // filter some records out: the open group should stay open but now
            // be empty
            filterEnabled = true;
            await model.reload(resultID);
            record = model.get(resultID);
            assert.strictEqual(record.data[0].count, 0,
                "first group's count should be 0");
            assert.strictEqual(record.data[0].data.length, 0,
                "first group's data should be empty'");
            model.destroy();
        });

        QUnit.test('group on date field with magic grouping method', async function (assert) {
            assert.expect(1);

            this.params.fieldNames = ['foo'];
            this.params.groupedBy = ['date:month'];
            this.params.res_id = undefined;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    if (args.method === 'web_read_group') {
                        assert.deepEqual(args.kwargs.fields, ['foo', 'date'],
                            "should have correctly trimmed the magic grouping info from the field name");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            await model.load(this.params);
            model.destroy();
        });


        QUnit.test('read group when grouped by a selection field', async function (assert) {
            assert.expect(5);

            this.data.partner.fields.selection = {
                type: 'selection',
                selection: [['a', 'A'], ['b', 'B']],
            };
            this.data.partner.records[0].selection = 'a';

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });
            var params = {
                modelName: 'partner',
                fields: this.data.partner.fields,
                fieldNames: ['foo'],
                groupedBy: ['selection'],
            };

            var resultID = await model.load(params);
            var dataPoint = model.get(resultID);
            assert.strictEqual(dataPoint.data.length, 2, "should have two groups");

            var groupFalse = _.findWhere(dataPoint.data, { value: false });
            assert.ok(groupFalse, "should have a group for value false");
            assert.deepEqual(groupFalse.domain, [['selection', '=', false]],
                "group's domain should be correct");

            var groupA = _.findWhere(dataPoint.data, { value: 'A' });
            assert.ok(groupA, "should have a group for value 'a'");
            assert.deepEqual(groupA.domain, [['selection', '=', 'a']],
                "group's domain should be correct");
            model.destroy();
        });

        QUnit.test('create record, then save', async function (assert) {
            assert.expect(5);

            this.params.fieldNames = ['product_ids'];
            this.params.res_id = undefined;
            this.params.type = 'record';
            this.params.context = { active_field: 2 };

            var id;
            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    if (args.method === 'create') {
                        // has to be done before the call to _super
                        assert.deepEqual(args.args[0].product_ids, [], "should not have any command");
                        assert.notOk('category' in args.args[0], "should not have other fields");

                        assert.strictEqual(args.kwargs.context.active_field, 2,
                            "record's context should be correctly passed");
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

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            await model.save(record.id, { reload: false });
            record = model.get(resultID);
            assert.strictEqual(record.res_id, id, "should have correct id from server");
            assert.strictEqual(record.data.id, id, "should have correct id from server");
            model.destroy();
        });

        QUnit.test('write commands on a one2many', async function (assert) {
            assert.expect(4);

            this.data.partner.records[1].product_ids = [37];

            this.params.fieldNames = ['product_ids'];

            var model = await createModel({
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

            var resultID = await model.load(this.params);
            var record = model.get(resultID, { raw: true });
            assert.deepEqual(record.data.product_ids, [37], "should have correct initial value");

            var relatedRecordID = await model.makeRecord('product', [{
                name: 'name',
                string: "Product Name",
                type: "char",
                value: "xpod"
            }
            ]);
            await model.notifyChanges(record.id, {
                product_ids: { operation: "ADD", id: relatedRecordID }
            });
            await model.save(record.id);
            model.destroy();
        });

        QUnit.test('create commands on a one2many', async function (assert) {
            assert.expect(3);

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    return this._super(route, args);
                },
            });

            this.params.fieldsInfo = {
                default: {
                    product_ids: {
                        fieldsInfo: {
                            default: {
                                display_name: { type: 'string' },
                            }
                        },
                        viewType: 'default',
                    }
                }
            };
            this.params.res_id = undefined;
            this.params.type = 'record';

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_ids.data.length, 0,
                "one2many should start with a list of length 0");

            await model.notifyChanges(record.id, {
                product_ids: {
                    operation: "CREATE",
                    data: {
                        display_name: 'coucou',
                    },
                },
            });
            record = model.get(resultID);
            assert.strictEqual(record.data.product_ids.data.length, 1,
                "one2many should be a list of length 1");
            assert.strictEqual(record.data.product_ids.data[0].data.display_name, "coucou",
                "one2many should have correct data");
            model.destroy();
        });

        QUnit.test('onchange with a one2many on a new record', async function (assert) {
            assert.expect(4);

            this.data.partner.fields.total.default = 50;
            this.data.partner.fields.product_ids.onChange = true;
            this.data.partner.onchanges.product_ids = function (obj) {
                obj.total += 100;
            };

            this.params.fieldNames = ['total', 'product_ids'];
            this.params.res_id = undefined;
            this.params.type = 'record';
            this.params.fieldsInfo = {
                form: {
                    product_ids: {
                        fieldsInfo: {
                            default: { name: {} },
                        },
                        relatedFields: this.data.product.fields,
                        viewType: 'default',
                    },
                    total: {},
                },
            };
            this.params.viewType = 'form';

            var o2mRecordParams = {
                fields: this.data.product.fields,
                fieldNames: ['name'],
                modelName: 'product',
                type: 'record',
            };

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    if (args.method === 'onchange' && args.args[1].total === 150) {
                        assert.deepEqual(args.args[1].product_ids, [[0, args.args[1].product_ids[0][1], { name: "xpod" }]],
                            "Should have sent the create command in the onchange");
                    }
                    return this._super(route, args);
                },
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.product_ids.data.length, 0,
                "one2many should start with a list of length 0");

            // make a default record for the related model
            var relatedRecordID = await model.load(o2mRecordParams);
            // update the subrecord
            await model.notifyChanges(relatedRecordID, { name: 'xpod' });
            // add the subrecord to the o2m of the main record
            await model.notifyChanges(resultID, {
                product_ids: { operation: "ADD", id: relatedRecordID }
            });

            record = model.get(resultID);
            assert.strictEqual(record.data.product_ids.data.length, 1,
                "one2many should be a list of length 1");
            assert.strictEqual(record.data.product_ids.data[0].data.name, "xpod",
                "one2many should have correct data");
            model.destroy();
        });

        QUnit.test('dates are properly loaded and parsed (record)', async function (assert) {
            assert.expect(2);

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var params = {
                fieldNames: ['date'],
                fields: this.data.partner.fields,
                modelName: 'partner',
                res_id: 1,
            };

            await model.load(params).then(function (resultID) {
                var record = model.get(resultID);
                assert.ok(record.data.date instanceof moment,
                    "fetched date field should have been formatted");
            });

            params.res_id = 2;

            await model.load(params).then(function (resultID) {
                var record = model.get(resultID);
                assert.strictEqual(record.data.date, false,
                    "unset date field should be false");
            });
            model.destroy();
        });

        QUnit.test('dates are properly loaded and parsed (list)', async function (assert) {
            assert.expect(2);

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var params = {
                fieldNames: ['date'],
                fields: this.data.partner.fields,
                modelName: 'partner',
                type: 'list',
            };

            await model.load(params).then(function (resultID) {
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

        QUnit.test('dates are properly loaded and parsed (default_get)', async function (assert) {
            assert.expect(1);

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var params = {
                fieldNames: ['date'],
                fields: this.data.partner.fields,
                modelName: 'partner',
                type: 'record',
            };

            await model.load(params).then(function (resultID) {
                var record = model.get(resultID);
                assert.strictEqual(record.data.date, false, "date default value should be false");
            });
            model.destroy();
        });

        QUnit.test('default_get on x2many may return a list of ids', async function (assert) {
            assert.expect(1);

            this.data.partner.fields.category.default = [12, 14];

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var params = {
                fieldNames: ['category'],
                fields: this.data.partner.fields,
                modelName: 'partner',
                type: 'record',
            };

            await model.load(params).then(function (resultID) {
                var record = model.get(resultID);
                assert.ok(_.isEqual(record.data.category.res_ids, [12, 14]),
                    "category field should have correct default value");
            });

            model.destroy();
        });

        QUnit.test('default_get: fetch many2one with default (empty & not) inside x2manys', async function (assert) {
            assert.expect(3);

            this.data.partner.fields.category_m2o = {
                type: 'many2one',
                relation: 'partner_type',
            };
            this.data.partner.fields.o2m = {
                string: "O2M", type: 'one2many', relation: 'partner', default: [
                    [6, 0, []],
                    [0, 0, { category_m2o: false, o2m: [] }],
                    [0, 0, { category_m2o: 12, o2m: [] }],
                ],
            };

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var params = {
                fieldNames: ['o2m'],
                fields: this.data.partner.fields,
                fieldsInfo: {
                    form: {
                        o2m: {
                            relatedFields: this.data.partner.fields,
                            fieldsInfo: {
                                list: {
                                    category_m2o: {
                                        relatedFields: { display_name: {} },
                                    },
                                },
                            },
                            viewType: 'list',
                        },
                    },
                },
                modelName: 'partner',
                type: 'record',
                viewType: 'form',
            };

            var resultID = await model.load(params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.o2m.count, 2, "o2m field should contain 2 records");
            assert.strictEqual(record.data.o2m.data[0].data.category_m2o, false,
                "first category field should be empty");
            assert.strictEqual(record.data.o2m.data[1].data.category_m2o.data.display_name, "gold",
                "second category field should have been correctly fetched");

            model.destroy();
        });

        QUnit.test('default_get: fetch x2manys inside x2manys', async function (assert) {
            assert.expect(3);

            this.data.partner.fields.o2m = {
                string: "O2M", type: 'one2many', relation: 'partner', default: [[6, 0, [1]]],
            };

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var params = {
                fieldNames: ['o2m'],
                fields: this.data.partner.fields,
                fieldsInfo: {
                    form: {
                        o2m: {
                            relatedFields: this.data.partner.fields,
                            fieldsInfo: {
                                list: {
                                    category: {
                                        relatedFields: { display_name: {} },
                                    },
                                },
                            },
                            viewType: 'list',
                        },
                    },
                },
                modelName: 'partner',
                type: 'record',
                viewType: 'form',
            };

            var resultID = await model.load(params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.o2m.count, 1, "o2m field should contain 1 record");
            var categoryList = record.data.o2m.data[0].data.category;
            assert.strictEqual(categoryList.count, 1,
                "category field should contain 1 record");
            assert.strictEqual(categoryList.data[0].data.display_name,
                'gold', "category records should have been fetched");

            model.destroy();
        });

        QUnit.test('contexts and domains can be properly fetched', async function (assert) {
            assert.expect(8);

            this.data.partner.fields.product_id.context = "{'hello': 'world', 'test': foo}";
            this.data.partner.fields.product_id.domain = "[['hello', 'like', 'world'], ['test', 'like', foo]]";

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            this.params.fieldNames = ['product_id', 'foo'];

            var resultID = await model.load(this.params);
            var recordPartner = model.get(resultID);
            assert.strictEqual(typeof recordPartner.getContext, "function",
                "partner record should have a getContext function");
            assert.strictEqual(typeof recordPartner.getDomain, "function",
                "partner record should have a getDomain function");
            assert.deepEqual(recordPartner.getContext(), {},
                "asking for a context without a field name should fetch the session/user/view context");
            assert.deepEqual(recordPartner.getDomain(), [],
                "asking for a domain without a field name should fetch the session/user/view domain");
            assert.deepEqual(
                recordPartner.getContext({ fieldName: "product_id" }),
                { hello: "world", test: "gnap" },
                "asking for a context with a field name should fetch the field context (evaluated)");
            assert.deepEqual(
                recordPartner.getDomain({ fieldName: "product_id" }),
                [["hello", "like", "world"], ["test", "like", "gnap"]],
                "asking for a domain with a field name should fetch the field domain (evaluated)");
            model.destroy();

            // Try again with xml override of field domain and context
            model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            this.params.fieldsInfo = {
                default: {
                    foo: {},
                    product_id: {
                        context: "{'hello2': 'world', 'test2': foo}",
                        domain: "[['hello2', 'like', 'world'], ['test2', 'like', foo]]",
                    },
                }
            };

            resultID = await model.load(this.params);
            recordPartner = model.get(resultID);
            assert.deepEqual(
                recordPartner.getContext({ fieldName: "product_id" }),
                { hello2: "world", test2: "gnap" },
                "field context should have been overridden by xml attribute");
            assert.deepEqual(
                recordPartner.getDomain({ fieldName: "product_id" }),
                [["hello2", "like", "world"], ["test2", "like", "gnap"]],
                "field domain should have been overridden by xml attribute");
            model.destroy();
        });

        QUnit.test('dont write on readonly fields (write and create)', async function (assert) {
            assert.expect(6);

            this.params.fieldNames = ['foo', 'bar'];
            this.data.partner.fields.foo.onChange = true;
            this.data.partner.onchanges.foo = function (obj) {
                obj.bar = obj.foo.length;
            };
            this.params.fieldsInfo = {
                default: {
                    foo: {},
                    bar: {
                        modifiers: {
                            readonly: true,
                        },
                    },
                }
            };

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    if (args.method === 'write') {
                        assert.deepEqual(args.args[1], { foo: "verylongstring" },
                            "should only save foo field");
                    }
                    if (args.method === 'create') {
                        assert.deepEqual(args.args[0], { foo: "anotherverylongstring" },
                            "should only save foo field");
                    }
                    return this._super(route, args);
                },
            });
            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.bar, 2,
                "should be initialized with correct value");

            await model.notifyChanges(resultID, { foo: "verylongstring" });

            record = model.get(resultID);
            assert.strictEqual(record.data.bar, 14,
                "should be changed with correct value");

            await model.save(resultID);

            // start again, but with a new record
            delete this.params.res_id;
            resultID = await model.load(this.params);
            record = model.get(resultID);
            assert.strictEqual(record.data.bar, 0,
                "should be initialized with correct value (0 as integer)");

            await model.notifyChanges(resultID, { foo: "anotherverylongstring" });

            record = model.get(resultID);
            assert.strictEqual(record.data.bar, 21,
                "should be changed with correct value");

            await model.save(resultID);
            model.destroy();
        });

        QUnit.test('dont write on readonly fields unless save attribute is set', async function (assert) {
            assert.expect(6);

            this.params.fieldNames = ['foo', 'bar'];
            this.data.partner.fields.foo.onChange = true;
            this.data.partner.onchanges.foo = function (obj) {
                obj.bar = obj.foo.length;
            };
            this.params.fieldsInfo = {
                default: {
                    foo: {},
                    bar: {
                        modifiers: {
                            readonly: true,
                        },
                        force_save: true,
                    },
                }
            };

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    if (args.method === 'write') {
                        assert.deepEqual(args.args[1], { bar: 14, foo: "verylongstring" },
                            "should only save foo field");
                    }
                    if (args.method === 'create') {
                        assert.deepEqual(args.args[0], { bar: 21, foo: "anotherverylongstring" },
                            "should only save foo field");
                    }
                    return this._super(route, args);
                },
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.bar, 2,
                "should be initialized with correct value");

            await model.notifyChanges(resultID, { foo: "verylongstring" });

            record = model.get(resultID);
            assert.strictEqual(record.data.bar, 14,
                "should be changed with correct value");

            await model.save(resultID);

            // start again, but with a new record
            delete this.params.res_id;
            resultID = await model.load(this.params);
            record = model.get(resultID);
            assert.strictEqual(record.data.bar, 0,
                "should be initialized with correct value (0 as integer)");

            await model.notifyChanges(resultID, { foo: "anotherverylongstring" });

            record = model.get(resultID);
            assert.strictEqual(record.data.bar, 21,
                "should be changed with correct value");

            await model.save(resultID);
            model.destroy();
        });

        QUnit.test('default_get with one2many values', async function (assert) {
            assert.expect(1);

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    if (args.method === 'default_get') {
                        return Promise.resolve({
                            product_ids: [[0, 0, { "name": "xdroid" }]]
                        });
                    }
                    return this._super(route, args);
                },
            });
            var params = {
                fieldNames: ['product_ids'],
                fields: this.data.partner.fields,
                modelName: 'partner',
                type: 'record',
                fieldsInfo: {
                    form: {
                        product_ids: {
                            fieldsInfo: {
                                default: { name: {} },
                            },
                            relatedFields: this.data.product.fields,
                            viewType: 'default',
                        },
                    },
                },
                viewType: 'form',
            };
            var resultID = await model.load(params);
            assert.strictEqual(typeof resultID, 'string', "result should be a valid id");
            model.destroy();
        });

        QUnit.test('call makeRecord with a pre-fetched many2one field', async function (assert) {
            assert.expect(3);
            var rpcCount = 0;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    rpcCount++;
                    return this._super(route, args);
                },
            });

            model.makeRecord('coucou', [{
                name: 'partner_id',
                relation: 'partner',
                type: 'many2one',
                value: [1, 'first partner'],
            }], {
                    partner_id: {
                        options: {
                            no_open: true,
                        },
                    },
                }).then(function (recordID) {
                    var record = model.get(recordID);
                    assert.deepEqual(record.fieldsInfo.default.partner_id, { options: { no_open: true } },
                        "makeRecord should have generated the fieldsInfo");
                    assert.deepEqual(record.data.partner_id.data, { id: 1, display_name: 'first partner' },
                        "many2one should contain the partner with id 1");
                    assert.strictEqual(rpcCount, 0, "makeRecord should not have done any rpc");
                });
            model.destroy();
        });

        QUnit.test('call makeRecord with a many2many field', async function (assert) {
            assert.expect(5);
            var rpcCount = 0;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    rpcCount++;
                    return this._super(route, args);
                },
            });

            var recordID = await model.makeRecord('coucou', [{
                name: 'partner_ids',
                fields: [{
                    name: 'id',
                    type: 'integer',
                }, {
                    name: 'display_name',
                    type: 'char',
                }],
                relation: 'partner',
                type: 'many2many',
                value: [1, 2],
            }]);
            var record = model.get(recordID);
            assert.deepEqual(record.fieldsInfo.default.partner_ids, {},
                "makeRecord should have generated the fieldsInfo");
            assert.strictEqual(record.data.partner_ids.count, 2,
                "there should be 2 elements in the many2many");
            assert.strictEqual(record.data.partner_ids.data.length, 2,
                "many2many should be a list of length 2");
            assert.deepEqual(record.data.partner_ids.data[0].data, { id: 1, display_name: 'first partner' },
                "many2many should contain the partner with id 1");
            assert.strictEqual(rpcCount, 1, "makeRecord should have done 1 rpc");
            model.destroy();
        });

        QUnit.test('call makeRecord with a pre-fetched many2many field', async function (assert) {
            assert.expect(5);
            var rpcCount = 0;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    rpcCount++;
                    return this._super(route, args);
                },
            });

            var recordID = await model.makeRecord('coucou', [{
                name: 'partner_ids',
                fields: [{
                    name: 'id',
                    type: 'integer',
                }, {
                    name: 'display_name',
                    type: 'char',
                }],
                relation: 'partner',
                type: 'many2many',
                value: [{
                    id: 1,
                    display_name: "first partner",
                }, {
                    id: 2,
                    display_name: "second partner",
                }],
            }]);
            var record = model.get(recordID);
            assert.deepEqual(record.fieldsInfo.default.partner_ids, {},
                "makeRecord should have generated the fieldsInfo");
            assert.strictEqual(record.data.partner_ids.count, 2,
                "there should be 2 elements in the many2many");
            assert.strictEqual(record.data.partner_ids.data.length, 2,
                "many2many should be a list of length 2");
            assert.deepEqual(record.data.partner_ids.data[0].data, { id: 1, display_name: 'first partner' },
                "many2many should contain the partner with id 1");
            assert.strictEqual(rpcCount, 0, "makeRecord should not have done any rpc");
            model.destroy();
        });

        QUnit.test('call makeRecord with a selection field', async function (assert) {
            assert.expect(4);
            var rpcCount = 0;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    rpcCount++;
                    return this._super.apply(this, arguments);
                },
            });

            var recordID = await model.makeRecord('partner', [{
                name: 'status',
                string: 'Status',
                type: 'selection',
                selection: [['draft', 'Draft'], ['done', 'Done'], ['failed', 'Failed']],
                value: 'done',
            }]);
            var record = model.get(recordID);
            assert.deepEqual(record.fieldsInfo.default.status, {},
                "makeRecord should have generated the fieldsInfo");
            assert.strictEqual(record.data.status, 'done',
                "should have a value 'done'");
            assert.strictEqual(record.fields.status.selection.length, 3,
                "should have 3 keys for selection");
            assert.strictEqual(rpcCount, 0, "makeRecord should have done 0 rpc");
            model.destroy();
        });

        QUnit.test('call makeRecord with a reference field', async function (assert) {
            assert.expect(2);
            let rpcCount = 0;

            const model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    rpcCount++;
                    return this._super(route, args);
                },
            });

            const field = this.data.partner.fields.reference;
            const recordID = await model.makeRecord('coucou', [{
                name: 'reference',
                type: 'reference',
                selection: field.selection,
                value: 'product,37',
            }]);
            const record = model.get(recordID);
            assert.deepEqual(record.data.reference.data, { id: 37, display_name: 'xphone' });
            assert.strictEqual(rpcCount, 1);

            model.destroy();
        });

        QUnit.test('check id, active_id, active_ids, active_model values in record\'s context', async function (assert) {
            assert.expect(2);

            this.data.partner.fields.product_id.context = "{'id': id, 'active_id': active_id, 'active_ids': active_ids, 'active_model': active_model}";

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            this.params.fieldNames = ['product_id'];

            var resultID = await model.load(this.params);
            var recordPartner = model.get(resultID);
            assert.deepEqual(
                recordPartner.getContext({ fieldName: "product_id" }),
                { id: 2, active_id: 2, active_ids: [2], active_model: "partner" },
                "wrong values for id, active_id, active_ids or active_model");

            // Try again without record
            this.params.res_id = undefined;

            resultID = await model.load(this.params);
            recordPartner = model.get(resultID);
            assert.deepEqual(
                recordPartner.getContext({ fieldName: "product_id" }),
                { id: false, active_id: false, active_ids: [], active_model: "partner" },
                "wrong values for id, active_id, active_ids or active_model. Have to be defined even if there is no record.");

            model.destroy();
        });

        QUnit.test('load model with many2many field properly fetched', async function (assert) {
            assert.expect(2);

            this.params.fieldNames = ['category'];
            this.params.res_id = 1;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super(route, args);
                },
            });

            await model.load(this.params);
            assert.verifySteps(['read'],
                "there should be only one read");
            model.destroy();
        });

        QUnit.test('data should contain all fields in view, default being false', async function (assert) {
            assert.expect(1);

            this.data.partner.fields.product_ids.default = [
                [6, 0, []],
                [0, 0, { name: 'new' }],
            ];
            this.data.product.fields.date = { string: "Date", type: "date" };

            var params = {
                fieldNames: ['product_ids'],
                modelName: 'partner',
                fields: this.data.partner.fields,
                fieldsInfo: {
                    form: {
                        product_ids: {
                            relatedFields: this.data.product.fields,
                            fieldsInfo: { list: { name: {}, date: {} } },
                            viewType: 'list',
                        }
                    },
                },
                res_id: undefined,
                type: 'record',
                viewType: 'form',
            };

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            await model.load(params).then(function (resultID) {
                var record = model.get(resultID);
                assert.strictEqual(record.data.product_ids.data[0].data.date, false,
                    "date value should be in data, and should be false");
            });

            model.destroy();
        });

        QUnit.test('changes are discarded when reloading from a new record', async function (assert) {
            // practical use case: click on 'Create' to open a form view in edit
            // mode (new record), click on 'Discard', then open an existing record
            assert.expect(2);

            this.data.partner.fields.foo.default = 'default';
            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            // load a new record (default_get)
            var params = _.extend(this.params, {
                res_id: undefined,
                type: 'record',
                fieldNames: ['foo'],
            });
            var resultID = await model.load(params);
            var record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'default',
                "should be the default value");

            // reload with id 2
            resultID = await model.reload(record.id, { currentId: 2 });
            record = model.get(resultID);
            assert.strictEqual(record.data.foo, 'gnap',
                "should be the value of record 2");

            model.destroy();
        });

        QUnit.test('has a proper evaluation context', async function (assert) {
            assert.expect(6);

            const unpatchDate = testUtils.mock.patchDate(1997, 0, 9, 12, 0, 0);
            this.params.fieldNames = Object.keys(this.data.partner.fields);
            this.params.res_id = 1;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            const { evalContext } = model.get(resultID);
            assert.strictEqual(typeof evalContext.datetime, "object");
            assert.strictEqual(typeof evalContext.relativedelta, "object");
            assert.strictEqual(typeof evalContext.time, "object");
            assert.strictEqual(typeof evalContext.context_today, "function");
            assert.strictEqual(typeof evalContext.tz_offset, "function");
            const blackListedKeys = [
                "time",
                "datetime",
                "relativedelta",
                "context_today",
                "tz_offset",
            ];
            // Remove uncomparable values from the evaluation context
            for (const key of blackListedKeys) {
                delete evalContext[key];
            }
            assert.deepEqual(evalContext, {
                active: true,
                active_id: 1,
                active_ids: [1],
                active_model: "partner",
                bar: 1,
                category: [12],
                current_company_id: false,
                current_date: moment().format('YYYY-MM-DD'),
                today: moment().format('YYYY-MM-DD'),
                now: moment().utc().format('YYYY-MM-DD HH:mm:ss'),
                date: "2017-01-25",
                display_name: "first partner",
                foo: "blip",
                id: 1,
                product_id: 37,
                product_ids: [],
                qux: false,
                reference: false,
                total: 0,
                x_active: true,
            }, "should use the proper eval context");
            model.destroy();
            unpatchDate();
        });

        QUnit.test('x2manys in contexts and domains are correctly evaluated', async function (assert) {
            assert.expect(4);

            this.data.partner.records[0].product_ids = [37, 41];
            this.params.fieldNames = Object.keys(this.data.partner.fields);
            this.params.fieldsInfo = {
                form: {
                    qux: {
                        context: "{'category': category, 'product_ids': product_ids}",
                        domain: "[['id', 'in', category], ['id', 'in', product_ids]]",
                        relatedFields: this.data.partner.fields,
                    },
                    category: {
                        relatedFields: this.data.partner_type.fields,
                    },
                    product_ids: {
                        relatedFields: this.data.product.fields,
                    },
                },
            };
            this.params.viewType = 'form';
            this.params.res_id = 1;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            var context = record.getContext({ fieldName: 'qux' });
            var domain = record.getDomain({ fieldName: 'qux' });

            assert.deepEqual(context, {
                category: [12],
                product_ids: [37, 41],
            }, "x2many values in context manipulated client-side should be lists of ids");
            assert.strictEqual(JSON.stringify(context),
                "{\"category\":[[6,false,[12]]],\"product_ids\":[[4,37,false],[4,41,false]]}",
                "x2many values in context sent to the server should be commands");
            assert.deepEqual(domain, [
                ['id', 'in', [12]],
                ['id', 'in', [37, 41]],
            ], "x2many values in domains should be lists of ids");
            assert.strictEqual(JSON.stringify(domain),
                "[[\"id\",\"in\",[12]],[\"id\",\"in\",[37,41]]]",
                "x2many values in domains should be lists of ids");
            model.destroy();
        });

        QUnit.test('fetch references in list, with not too many rpcs', async function (assert) {
            assert.expect(5);

            this.data.partner.records[0].reference = 'product,37';
            this.data.partner.records[1].reference = 'product,41';

            this.params.fieldNames = ['reference'];
            this.params.domain = [];
            this.params.groupedBy = [];
            this.params.res_id = undefined;

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    assert.step(route);
                    if (route === "/web/dataset/call_kw/product/name_get") {
                        assert.deepEqual(args.args, [[37, 41]],
                            "the name_get should contain the product ids");
                    }
                    return this._super(route, args);
                },
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);

            assert.strictEqual(record.data[0].data.reference.data.display_name, "xphone",
                "name_get should have been correctly fetched");
            assert.verifySteps(["/web/dataset/search_read", "/web/dataset/call_kw/product/name_get"],
                "should have done 2 rpc (searchread and name_get for product)");
            model.destroy();
        });

        QUnit.test('reload a new record', async function (assert) {
            assert.expect(6);

            this.params.context = {};
            this.params.fieldNames = ['product_id', 'category', 'product_ids'];
            this.params.res_id = undefined;
            this.params.type = 'record';

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super(route, args);
                },
            });

            var recordID = await model.load(this.params);
            recordID = await model.reload(recordID);
            assert.verifySteps(['onchange', 'onchange']);
            var record = model.get(recordID);
            assert.strictEqual(record.data.product_id, false,
                "m2o default value should be false");
            assert.deepEqual(record.data.product_ids.data, [],
                "o2m default should be []");
            assert.deepEqual(record.data.category.data, [],
                "m2m default should be []");

            model.destroy();
        });

        QUnit.test('default_get with value false for a one2many', async function (assert) {
            assert.expect(1);

            this.data.partner.fields.product_ids.default = false;
            this.params.fieldNames = ['product_ids'];
            this.params.res_id = undefined;
            this.params.type = 'record';

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.deepEqual(record.data.product_ids.data, [], "o2m default should be []");

            model.destroy();
        });

        QUnit.test('only x2many lists (static) should be sorted client-side', async function (assert) {
            assert.expect(1);

            this.params.modelName = 'partner_type';
            this.params.res_id = undefined;
            this.params.orderedBy = [{ name: 'display_name', asc: true }];

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
                mockRPC: function (route) {
                    if (route === '/web/dataset/search_read') {
                        // simulate randomn sort form the server
                        return Promise.resolve({
                            length: 3,
                            records: [
                                { id: 12, display_name: "gold", date: "2017-01-25" },
                                { id: 15, display_name: "bronze" },
                                { id: 14, display_name: "silver" },
                            ],
                        });
                    }
                    return this._super.apply(this, arguments);
                },
            });

            var resultID = await model.load(this.params);
            var list = model.get(resultID);
            assert.deepEqual(_.map(list.data, 'res_id'), [12, 15, 14],
                "should have kept the order from the server");
            model.destroy();
        });

        QUnit.test('onchange on a boolean field', async function (assert) {
            assert.expect(2);

            var newFields = {
                foobool: {
                    type: 'boolean',
                    string: 'foobool',
                },
                foobool2: {
                    type: 'boolean',
                    string: 'foobool2',
                },
            };
            _.extend(this.data.partner.fields, newFields);

            this.data.partner.fields.foobool.onChange = true;
            this.data.partner.onchanges.foobool = function (obj) {
                if (obj.foobool) {
                    obj.foobool2 = true;
                }
            };

            this.data.partner.records[0].foobool = false;
            this.data.partner.records[0].foobool2 = true;

            this.params.res_id = 1;
            this.params.fieldNames = ['foobool', 'foobool2'];
            this.params.fields = this.data.partner.fields;
            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            await model.notifyChanges(resultID, { foobool2: false });
            record = model.get(resultID);
            assert.strictEqual(record.data.foobool2, false, "foobool2 field should be false");
            await model.notifyChanges(resultID, { foobool: true });
            record = model.get(resultID);
            assert.strictEqual(record.data.foobool2, true, "foobool2 field should be true");
            model.destroy();
        });

        QUnit.test('notifyChange DELETE_ALL on a one2many', async function (assert) {
            assert.expect(5);

            this.data.partner.records[1].product_ids = [37, 38];
            this.params.fieldNames = ['product_ids'];

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var o2mParams = {
                modelName: 'product',
                fields: this.data.product.fields,
            };

            var resultID = await model.load(this.params);
            var newRecordID = await model.load(o2mParams);
            var record = model.get(resultID);
            var x2mListID = record.data.product_ids.id;

            assert.strictEqual(record.data.product_ids.count, 2,
                "there should be two records in the relation");

            await model.notifyChanges(resultID, {product_ids: {operation: 'ADD', id: newRecordID}});

            assert.deepEqual(model.localData[x2mListID]._changes, [{
                operation: 'ADD', id: newRecordID,
            }], "_changes should be correct");

            record = model.get(resultID);
            assert.strictEqual(record.data.product_ids.count, 3,
                "there should be three records in the relation");

            await model.notifyChanges(resultID, {product_ids: {operation: 'DELETE_ALL'}});

            assert.deepEqual(model.localData[x2mListID]._changes, [{
                id: 37,
                operation: "DELETE"
            }, {
                id: 38,
                operation: "DELETE"
            }], "_changes should contain the two 'DELETE' operations");

            record = model.get(resultID);
            assert.strictEqual(record.data.product_ids.count, 0,
                "there should be no more records in the relation");
            model.destroy();
        });

        QUnit.test('notifyChange MULTI on a one2many', async function (assert) {
            assert.expect(4);

            this.data.partner.records[1].product_ids = [37, 38];
            this.params.fieldNames = ['product_ids'];

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var o2mParams = {
                modelName: 'product',
                fields: this.data.product.fields,
            };

            var resultID = await model.load(this.params);
            var newRecordID = await model.load(o2mParams);
            var record = model.get(resultID);
            var x2mListID = record.data.product_ids.id;

            assert.strictEqual(record.data.product_ids.count, 2,
                "there should be two records in the relation");

            await model.notifyChanges(resultID, {product_ids: {
                operation: 'MULTI',
                commands: [{
                    operation: 'DELETE_ALL'
                }, {
                    operation: 'ADD',
                    id: newRecordID
                }]
            }});

            assert.deepEqual(model.localData[x2mListID]._changes, [{
                id: 37,
                operation: "DELETE"
            }, {
                id: 38,
                operation: "DELETE"
            }, {
                operation: 'ADD', id: newRecordID,
            }], "_changes should be correct");

            record = model.get(resultID);
            assert.strictEqual(record.data.product_ids.count, 1,
                "there should be one record in the relation");

            assert.strictEqual(record.data.product_ids.data[0].id, newRecordID,
                "the id should match");
        });

        QUnit.test('notifyChange MULTI on a many2many', async function (assert) {
            assert.expect(3);

            this.params.fieldsInfo = {
                default: {
                    category: {
                        fieldsInfo: {default: {some_char: { context: "{'a': parent.foo}"}}},
                        relatedFields: {some_char: {type: "char"}},
                        viewType: 'default',
                    },
                    foo: {},
                },
            };

            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });

            var resultID = await model.load(this.params);
            var changes = {
                category: {
                    operation: 'MULTI',
                    commands: [{
                        operation: 'ADD_M2M',
                        ids: [{id: 23}, {id: 24}, {id: 25}]
                    }, {
                        operation: 'ADD_M2M',
                        ids: [{id: 26}]
                    }]
                }
            };
            await model.notifyChanges(resultID, changes);
            var record = model.get(resultID);
            var categoryRecord = record.data.category;

            assert.strictEqual(categoryRecord.data.length, 4,
                "there should 2 records in the relation");

            await model.notifyChanges(resultID, {category: {
                operation: 'MULTI',
                commands: [{
                    operation: 'DELETE_ALL'
                }, {
                    operation: 'ADD_M2M',
                    ids: [{id: 27}]
                }]
            }});
            record = model.get(resultID);
            categoryRecord = record.data.category;
            assert.strictEqual(categoryRecord.data.length, 1,
                "there should 1 record in the relation");

            assert.strictEqual(record.data.category.data[0].data.id, 27,
                "the id should match");

            model.destroy();
        });

        QUnit.test('identify correct active field', async function(assert) {
            assert.expect(4);
            var model = await createModel({
                Model: BasicModel,
                data: this.data,
            });
            // check that active field is returned if present
            this.params.res_id = 37;
            this.params.modelName = 'product'
            this.params.fields = this.data.product.fields;
            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.equal(model.getActiveField(record), 'active', 'should have returned "active" field name');
            // check that active field is not returned if not present
            this.params.res_id = 42;
            this.params.modelName = 'partner_title';
            this.params.fields = this.data.partner_title.fields;
            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.equal(model.getActiveField(record), undefined, 'should not have returned any field name');
            // check that x_active field is returned if x_active present
            this.params.res_id = 12;
            this.params.modelName = 'partner_type';
            this.params.fields = this.data.partner_type.fields;
            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.equal(model.getActiveField(record), 'x_active', 'should have returned "x_active" field name');

            // check that active field is returned if both active and x_active present
            this.params.res_id = 1;
            this.params.modelName = 'partner';
            this.params.fields = this.data.partner.fields;
            var resultID = await model.load(this.params);
            var record = model.get(resultID);
            assert.equal(model.getActiveField(record), 'active', 'should have returned "active" field name');
        });
    });
});
