odoo.define('web.kanban_model_tests', function (require) {
"use strict";

var KanbanModel = require('web.KanbanModel');
var testUtils = require('web.test_utils');

var createModel = testUtils.createModel;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    active: {string: "Active", type: "boolean", default: true},
                    display_name: {string: "STRING", type: 'char'},
                    foo: {string: "Foo", type: 'char'},
                    bar: {string: "Bar", type: 'integer'},
                    qux: {string: "Qux", type: 'many2one', relation: 'partner'},
                    product_id: {string: "Favorite product", type: 'many2one', relation: 'product'},
                    product_ids: {string: "Favorite products", type: 'one2many', relation: 'product'},
                    category: {string: "Category M2M", type: 'many2many', relation: 'partner_type'},
                },
                records: [
                    {id: 1, foo: 'blip', bar: 1, product_id: 37, category: [12], display_name: "first partner"},
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
            fields: this.data.partner.fields,
            limit: 40,
            modelName: 'partner',
            openGroupByDefault: true,
            viewType: 'kanban',
        };
    },
}, function () {

    QUnit.module('KanbanModel');

    QUnit.test('load grouped + add a new group', async function (assert) {
        var done = assert.async();
        assert.expect(22);

        var calledRoutes = {};
        var model = createModel({
            Model: KanbanModel,
            data: this.data,
            mockRPC: function (route) {
                if (!(route in calledRoutes)) {
                    calledRoutes[route] = 1;
                } else {
                    calledRoutes[route]++;
                }
                return this._super.apply(this, arguments);
            },
        });

        var params = _.extend(this.params, {
            groupedBy: ['product_id'],
            fieldNames: ['foo'],
        });

        model.load(params).then(async function (resultID) {
            // various checks on the load result
            var state = model.get(resultID);
            assert.ok(_.isEqual(state.groupedBy, ['product_id']), 'should be grouped by "product_id"');
            assert.strictEqual(state.data.length, 2, 'should have found 2 groups');
            assert.strictEqual(state.count, 2, 'both groups contain one record');
            var xphoneGroup = _.findWhere(state.data, {res_id: 37});
            assert.strictEqual(xphoneGroup.model, 'partner', 'group should have correct model');
            assert.ok(xphoneGroup, 'should have a group for res_id 37');
            assert.ok(xphoneGroup.isOpen, '"xphone" group should be open');
            assert.strictEqual(xphoneGroup.value, 'xphone', 'group 37 should be "xphone"');
            assert.strictEqual(xphoneGroup.count, 1, '"xphone" group should have one record');
            assert.strictEqual(xphoneGroup.data.length, 1, 'should have fetched the records in the group');
            assert.ok(_.isEqual(xphoneGroup.domain[0], ['product_id', '=', 37]),
                'domain should be correct');
            assert.strictEqual(xphoneGroup.limit, 40, 'limit in a group should be 40');

            // add a new group
            await model.createGroup('xpod', resultID);
            state = model.get(resultID);
            assert.strictEqual(state.data.length, 3, 'should now have 3 groups');
            assert.strictEqual(state.count, 2, 'there are still 2 records');
            var xpodGroup = _.findWhere(state.data, {value: 'xpod'});
            assert.strictEqual(xpodGroup.model, 'partner', 'new group should have correct model');
            assert.ok(xpodGroup, 'should have an "xpod" group');
            assert.ok(xpodGroup.isOpen, 'new group should be open');
            assert.strictEqual(xpodGroup.count, 0, 'new group should contain no record');
            assert.ok(_.isEqual(xpodGroup.domain[0], ['product_id', '=', xpodGroup.res_id]),
                'new group should have correct domain');

            // check the rpcs done
            assert.strictEqual(Object.keys(calledRoutes).length, 3, 'three different routes have been called');
            var nbReadGroups = calledRoutes['/web/dataset/call_kw/partner/web_read_group'];
            var nbSearchRead = calledRoutes['/web/dataset/search_read'];
            var nbNameCreate = calledRoutes['/web/dataset/call_kw/product/name_create'];
            assert.strictEqual(nbReadGroups, 1, 'should have done 1 read_group');
            assert.strictEqual(nbSearchRead, 2, 'should have done 2 search_read');
            assert.strictEqual(nbNameCreate, 1, 'should have done 1 name_create');
            model.destroy();
            done();
        });
    });

    QUnit.test('archive/restore a column', async function (assert) {
        var done = assert.async();
        assert.expect(4);

        var model = createModel({
            Model: KanbanModel,
            data: this.data,
        });

        var params = _.extend(this.params, {
            groupedBy: ['product_id'],
            fieldNames: ['foo'],
        });

        model.load(params).then(async function (resultID) {
            var state = model.get(resultID);
            var xphoneGroup = _.findWhere(state.data, {res_id: 37});
            var xpadGroup = _.findWhere(state.data, {res_id: 41});
            assert.strictEqual(xphoneGroup.count, 1, 'xphone group has one record');
            assert.strictEqual(xpadGroup.count, 1, 'xpad group has one record');

            // archive the column 'xphone'
            var recordIDs = _.pluck(xphoneGroup.data, 'id');
            await model.toggleActive(recordIDs, false, xphoneGroup.id);
            state = model.get(resultID);
            xphoneGroup = _.findWhere(state.data, {res_id: 37});
            assert.strictEqual(xphoneGroup.count, 0, 'xphone group has no record anymore');
            xpadGroup = _.findWhere(state.data, {res_id: 41});
            assert.strictEqual(xpadGroup.count, 1, 'xpad group still has one record');
            model.destroy();
            done();
        });
    });

    QUnit.test('kanban model does not allow nested groups', async function (assert) {
        var done = assert.async();
        assert.expect(2);

        var model = createModel({
            Model: KanbanModel,
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    assert.deepEqual(args.kwargs.groupby, ['product_id'],
                        "the second level of groupBy should have been removed");
                }
                return this._super.apply(this, arguments);
            },
        });

        var params = _.extend(this.params, {
            groupedBy: ['product_id', 'qux'],
            fieldNames: ['foo'],
        });

        model.load(params).then(function (resultID) {
            var state = model.get(resultID);

            assert.deepEqual(state.groupedBy, ['product_id'],
                "the second level of groupBy should have been removed");

            model.destroy();
            done();
        });
    });

    QUnit.test('resequence columns and records', async function (assert) {
        var done = assert.async();
        assert.expect(8);

        this.data.product.fields.sequence = {string: "Sequence", type: "integer"};
        this.data.partner.fields.sequence = {string: "Sequence", type: "integer"};
        this.data.partner.records.push({id: 3, foo: 'aaa', product_id: 37});

        var nbReseq = 0;
        var model = createModel({
            Model: KanbanModel,
            data: this.data,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    nbReseq++;
                    if (nbReseq === 1) { // resequencing columns
                        assert.deepEqual(args.ids, [41, 37],
                            "ids should be correct");
                        assert.strictEqual(args.model, 'product',
                            "model should be correct");
                    } else if (nbReseq === 2) { // resequencing records
                        assert.deepEqual(args.ids, [3, 1],
                            "ids should be correct");
                        assert.strictEqual(args.model, 'partner',
                            "model should be correct");
                    }
                }
                return this._super.apply(this, arguments);
            },
        });
        var params = _.extend(this.params, {
            groupedBy: ['product_id'],
            fieldNames: ['foo'],
        });

        model.load(params)
            .then(function (stateID) {
                var state = model.get(stateID);
                assert.strictEqual(state.data[0].res_id, 37,
                    "first group should be res_id 37");

                // resequence columns
                return model.resequence('product', [41, 37], stateID);
            })
            .then(function (stateID) {
                var state = model.get(stateID);
                assert.strictEqual(state.data[0].res_id, 41,
                    "first group should be res_id 41 after resequencing");
                assert.strictEqual(state.data[1].data[0].res_id, 1,
                    "first record should be res_id 1");

                // resequence records
                return model.resequence('partner', [3, 1], state.data[1].id);
            })
            .then(function (groupID) {
                var group = model.get(groupID);
                assert.strictEqual(group.data[0].res_id, 3,
                    "first record should be res_id 3 after resequencing");

                model.destroy();
                done();
            });
    });

    QUnit.test('add record to group', async function (assert) {
        var done = assert.async();
        assert.expect(8);

        var self = this;
        var model = createModel({
            Model: KanbanModel,
            data: this.data,
        });
        var params = _.extend(this.params, {
            groupedBy: ['product_id'],
            fieldNames: ['foo'],
        });

        model.load(params).then(function (stateID) {
            self.data.partner.records.push({id: 3, foo: 'new record', product_id: 37});

            var state = model.get(stateID);
            assert.deepEqual(state.res_ids, [1, 2],
                "state should have the correct res_ids");
            assert.strictEqual(state.count, 2,
                "state should have the correct count");
            assert.strictEqual(state.data[0].count, 1,
                "first group should contain one record");

            return model.addRecordToGroup(state.data[0].id, 3).then(function () {
                var state = model.get(stateID);
                assert.deepEqual(state.res_ids, [3, 1, 2],
                    "state should have the correct res_ids");
                assert.strictEqual(state.count, 3,
                    "state should have the correct count");
                assert.deepEqual(state.data[0].res_ids, [3, 1],
                    "new record's id should have been added to the res_ids");
                assert.strictEqual(state.data[0].count, 2,
                    "first group should now contain two records");
                assert.strictEqual(state.data[0].data[0].data.foo, 'new record',
                    "new record should have been fetched");
            });
        }).then(function() {
            model.destroy();
            done();
        })

    });
});

});
