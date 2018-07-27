odoo.define('web.pivot_tests', function (require) {
"use strict";

var core = require('web.core');
var PivotView = require('web.PivotView');
var testUtils = require('web.test_utils');

var _t = core._t;
var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "integer"},
                    bar: {string: "bar", type: "boolean"},
                    date: {string: "Date", type: "date", store: true},
                    product_id: {string: "Product", type: "many2one", relation: 'product', store: true},
                    other_product_id: {string: "Other Product", type: "many2one", relation: 'product', store: true},
                    non_stored_m2o: {string: "Non Stored M2O", type: "many2one", relation: 'product'},
                    customer: {string: "Customer", type: "many2one", relation: 'customer', store: true},
                    computed_field: {string: "Computed and not stored", compute:true},
                },
                records: [
                    {
                        id: 1,
                        foo: 12,
                        bar: true,
                        date: '2016-12-14',
                        product_id: 37,
                        customer: 1,
                        computed_field: 19,
                    }, {
                        id: 2,
                        foo: 1,
                        bar: true,
                        date: '2016-10-26',
                        product_id: 41,
                        customer: 2,
                        computed_field: 23,
                    }, {
                        id: 3,
                        foo: 17,
                        bar: true,
                        date: '2016-12-15',
                        product_id: 41,
                        customer: 2,
                        computed_field: 26,
                    }, {id: 4,
                        foo: 2,
                        bar: false,
                        date: '2016-04-11',
                        product_id: 41,
                        customer: 1,
                        computed_field: 19,
                    },
                ]
            },
            product: {
                fields: {
                    name: {string: "Product Name", type: "char"}
                },
                records: [{
                    id: 37,
                    display_name: "xphone",
                }, {
                    id: 41,
                    display_name: "xpad",
                }]
            },
            customer: {
                fields: {
                    name: {string: "Customer Name", type: "char"}
                },
                records: [{
                    id: 1,
                    display_name: "First",
                }, {
                    id: 2,
                    display_name: "Second",
                }]
            },
        };
    }
}, function () {
    QUnit.module('PivotView');

    QUnit.test('simple pivot rendering', function (assert) {
        assert.expect(3);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners">' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
            mockRPC: function (route, args) {
                assert.strictEqual(args.kwargs.lazy, false,
                    "the read_group should be done with the lazy=false option");
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(pivot.$el.hasClass('o_enable_linking'),
            "root node should have classname 'o_enable_linking'");
        assert.strictEqual(pivot.$('td.o_pivot_cell_value:contains(32)').length, 1,
                    "should contain a pivot cell with the sum of all records");
        pivot.destroy();
    });

    QUnit.test('pivot view without "string" attribute', function (assert) {
        assert.expect(1);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        // this is important for export functionality.
        assert.strictEqual(pivot.title, _t("Untitled"), "should have a valid title");
        pivot.destroy();
    });

    QUnit.test('pivot view add computed fields explicitly defined as measure', function (assert) {
        assert.expect(1);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="computed_field" type="measure"/>' +
                '</pivot>',
        });

        assert.ok(pivot.measures.computed_field, "measures contains the field 'computed_field'");
        pivot.destroy();
    });

    QUnit.test('clicking on a cell triggers a do_action', function (assert) {
        assert.expect(2);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="row"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
            intercepts: {
                do_action: function (ev) {
                    assert.deepEqual(ev.data.action, {
                        context: {someKey: true, userContextKey: true},
                        domain: [['product_id', '=', 37]],
                        name: 'Partners',
                        res_model: 'partner',
                        target: 'current',
                        type: 'ir.actions.act_window',
                        view_mode: 'list',
                        view_type: 'list',
                        views: [[false, 'list'], [2, 'form']],
                    }, "should trigger do_action with the correct args");
                },
            },
            session: {
                user_context: {userContextKey: true},
            },
            viewOptions: {
                action: {
                    views: [
                        { viewID: 2, type: 'form' },
                        { viewID: 5, type: 'kanban' },
                        { viewID: false, type: 'list' },
                        { viewID: false, type: 'pivot' },
                    ],
                },
                context: {someKey: true, search_default_test: 3},
                title: 'Partners',
            }
        });

        assert.ok(pivot.$el.hasClass('o_enable_linking'),
            "root node should have classname 'o_enable_linking'");
        pivot.$('.o_pivot_cell_value:contains(12)').click(); // should trigger a do_action

        pivot.destroy();
    });

    QUnit.test('pivot view with disable_linking="True"', function (assert) {
        assert.expect(2);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot disable_linking="True">' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
            intercepts: {
                do_action: function () {
                    assert.ok(false, "should not trigger do_action");
                },
            },
        });

        assert.notOk(pivot.$el.hasClass('o_enable_linking'),
            "root node should not have classname 'o_enable_linking'");
        assert.strictEqual(pivot.$('.o_pivot_cell_value').length, 1,
            "should have one cell");
        pivot.$('.o_pivot_cell_value').click(); // should not trigger a do_action

        pivot.destroy();
    });

    QUnit.test('pivot view grouped by date field', function (assert) {
        assert.expect(2);

        var data = this.data;
        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="date" interval="month" type="col"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
            mockRPC: function (route, params) {
                var wrong_fields = _.filter(params.kwargs.fields, function (field) {
                    return !(field in data.partner.fields);
                });
                assert.ok(!wrong_fields.length, 'fields given to read_group should exist on the model');
                return this._super.apply(this, arguments);
            },
        });
        pivot.destroy();
    });

    QUnit.test('without measures, pivot view uses __count by default', function (assert) {
        assert.expect(2);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot></pivot>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.fields, ['__count'],
                        "should make a read_group with no valid fields");
                }
                return this._super(route, args);
            }
        });

        var $countMeasure = pivot.$buttons.find('.dropdown-item[data-field=__count]:first');
        assert.ok($countMeasure.hasClass('selected'), "The count measure should be activated");
        pivot.destroy();
    });

    QUnit.test('pivot view can be reloaded', function (assert) {
        assert.expect(4);
        var readGroupCount = 0;

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot></pivot>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    readGroupCount++;
                }
                return this._super(route, args);
            }
        });

        assert.strictEqual(pivot.$('td.o_pivot_cell_value:contains(4)').length, 1,
                    "should contain a pivot cell with the number of all records");
        assert.strictEqual(readGroupCount, 1, "should have done 1 rpc");

        pivot.update({domain: [['foo', '>', 10]]});
        assert.strictEqual(pivot.$('td.o_pivot_cell_value:contains(2)').length, 1,
                    "should contain a pivot cell with the number of remaining records");
        assert.strictEqual(readGroupCount, 2, "should have done 2 rpcs");
        pivot.destroy();
    });

    QUnit.test('pivot view grouped by many2one field', function (assert) {
        assert.expect(3);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="row"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        assert.strictEqual(pivot.$('.o_pivot_header_cell_opened').length, 1,
            "should have one opened header");
        assert.strictEqual(pivot.$('.o_pivot_header_cell_closed:contains(xphone)').length, 1,
            "should display one header with 'xphone'");
        assert.strictEqual(pivot.$('.o_pivot_header_cell_closed:contains(xpad)').length, 1,
            "should display one header with 'xpad'");
        pivot.destroy();
    });

    QUnit.test('basic folding/unfolding', function (assert) {
        assert.expect(7);

        var rpcCount = 0;

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="row"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
            mockRPC: function () {
                rpcCount++;
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(pivot.$('tbody tr').length, 3,
            "should have 3 rows: 1 for the opened header, and 2 for data");

        // click on the opened header to close it
        pivot.$('.o_pivot_header_cell_opened').click();

        assert.strictEqual(pivot.$('tbody tr').length, 1, "should have 1 row");

        // click on closed header to open dropdown
        pivot.$('tbody .o_pivot_header_cell_closed').click();

        assert.strictEqual(pivot.$('.o_pivot_field_menu .dropdown-item[data-field="date"]:first').length, 1,
            "should have the date field as proposition");
        assert.strictEqual(pivot.$('.o_field_selection .dropdown-item[data-field="product_id"]:first').length, 1,
            "should have the product_id field as proposition");
        assert.strictEqual(pivot.$('.o_field_selection .dropdown-item[data-field="non_stored_m2o"]:first').length, 0,
            "should not have the non_stored_m2o field as proposition");


        pivot.$('.o_pivot_field_menu .dropdown-item[data-field="date"]:first').click();

        assert.strictEqual(pivot.$('tbody tr').length, 4,
            "should have 4 rows: one for header, 3 for data");
        assert.strictEqual(rpcCount, 3,
            "should have done 3 rpcs (initial load) + open header with different groupbys");
        pivot.destroy();
    });

    QUnit.test('more folding/unfolding', function (assert) {
        assert.expect(1);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="row"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        // open dropdown to zoom into first row
        pivot.$('tbody .o_pivot_header_cell_closed').first().click();
        // click on date by day
        pivot.$('.o_pivot_field_menu .dropdown-item[data-field="date"][data-interval="day"]').click();

        // open dropdown to zoom into second row
        pivot.$('tbody td.o_pivot_header_cell_closed:eq(1)').first().click();

        assert.strictEqual(pivot.$('tbody tr').length, 7,
            "should have 7 rows (1 for total, 1 for xphone, 1 for xpad, 4 for data)");
        pivot.destroy();
    });

    QUnit.test('pivot view can be flipped', function (assert) {
        assert.expect(3);

        var rpcCount = 0;

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="row"/>' +
                '</pivot>',
            mockRPC: function () {
                rpcCount++;
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(pivot.$('tbody tr').length, 3,
            "should have 3 rows: 1 for the open header, and 2 for data");

        rpcCount = 0;
        pivot.$buttons.find('.o_pivot_flip_button').click();

        assert.strictEqual(rpcCount, 0, "should not have done any rpc");
        assert.strictEqual(pivot.$('tbody tr').length, 1,
            "should have 1 rows: 1 for the main header");
        pivot.destroy();
    });

    QUnit.test('can toggle extra measure', function (assert) {
        assert.expect(8);

        var rpcCount = 0;

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="row"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
            mockRPC: function () {
                rpcCount++;
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(pivot.$('.o_pivot_cell_value').length, 3,
            "should have 3 cells: 1 for the open header, and 2 for data");
        assert.ok(!pivot.$buttons.find('.dropdown-item[data-field=__count]:first').hasClass('selected'),
            "the __count measure should not be selected");

        rpcCount = 0;
        pivot.$buttons.find('.dropdown-item[data-field=__count]:first').click();

        assert.ok(pivot.$buttons.find('.dropdown-item[data-field=__count]:first').hasClass('selected'),
            "the __count measure should be selected");
        assert.strictEqual(pivot.$('.o_pivot_cell_value').length, 6,
            "should have 6 cells: 2 for the open header, and 4 for data");
        assert.strictEqual(rpcCount, 2,
            "should have done 2 rpcs to reload data");

        pivot.$buttons.find('.dropdown-item[data-field=__count]:first').click();

        assert.ok(!pivot.$buttons.find('.dropdown-item[data-field=__count]:first').hasClass('selected'),
            "the __count measure should not be selected");
        assert.strictEqual(pivot.$('.o_pivot_cell_value').length, 3,
            "should have 3 cells: 1 for the open header, and 2 for data");
        assert.strictEqual(rpcCount, 2,
            "should not have done any extra rpcs");
        pivot.destroy();
    });

    QUnit.test('no content helper when no active measure', function (assert) {
        assert.expect(4);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners">' +
                '</pivot>',
        });

        assert.strictEqual(pivot.$('.o_view_nocontent').length, 0,
            "should not have a no_content_helper");
        assert.strictEqual(pivot.$('table').length, 1,
            "should have a table in DOM");

        pivot.$buttons.find('.dropdown-item[data-field=__count]:first').click();

        assert.strictEqual(pivot.$('.o_view_nocontent').length, 1,
            "should have a no_content_helper");
        assert.strictEqual(pivot.$('table').length, 0,
            "should not have a table in DOM");
        pivot.destroy();
    });

    QUnit.test('no content helper when no data', function (assert) {
        assert.expect(4);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners">' +
                '</pivot>',
        });

        assert.strictEqual(pivot.$('.o_view_nocontent').length, 0,
            "should not have a no_content_helper");
        assert.strictEqual(pivot.$('table').length, 1,
            "should have a table in DOM");

        pivot.update({domain: [['foo', '=', 12345]]});

        assert.strictEqual(pivot.$('.o_view_nocontent').length, 1,
            "should have a no_content_helper");
        assert.strictEqual(pivot.$('table').length, 0,
            "should not have a table in DOM");
        pivot.destroy();
    });

    QUnit.test('no content helper when no data, part 2', function (assert) {
        assert.expect(1);

        this.data.partner.records = [];

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners"></pivot>',
        });

        assert.strictEqual(pivot.$('.o_view_nocontent').length, 1,
            "should have a no_content_helper");
        pivot.destroy();
    });

    QUnit.test('no content helper when no data, part 3', function (assert) {
        assert.expect(4);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners"></pivot>',
            viewOptions: {
                domain: [['foo', '=', 12345]]
            },
        });

        assert.strictEqual(pivot.$('.o_view_nocontent').length, 1,
            "should have a no_content_helper");
        pivot.update({domain: [['foo', '=', 12345]]});
        assert.strictEqual(pivot.$('.o_view_nocontent').length, 1,
            "should still have a no_content_helper");
        pivot.update({domain: []});
        assert.strictEqual(pivot.$('.o_view_nocontent').length, 0,
            "should not have a no_content_helper");

        // tries to open a field selection menu, to make sure it was not
        // removed from the dom.
        pivot.$('.o_pivot_header_cell_closed').first().click();
        assert.strictEqual(pivot.$('.o_pivot_field_menu').length, 1,
            "the field selector menu exists");
        pivot.destroy();
    });

    QUnit.test('tries to restore previous state after domain change', function (assert) {
        assert.expect(5);

        var rpcCount = 0;

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="row"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
            mockRPC: function () {
                rpcCount++;
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(pivot.$('.o_pivot_cell_value').length, 3,
            "should have 3 cells: 1 for the open header, and 2 for data");
        assert.strictEqual(pivot.$('.o_pivot_measure_row:contains(Foo)').length, 1,
            "should have 1 row for measure Foo");

        pivot.update({domain: [['foo', '=', 12345]]});

        rpcCount = 0;
        pivot.update({domain: []});

        assert.equal(rpcCount, 2, "should have reloaded data");
        assert.strictEqual(pivot.$('.o_pivot_cell_value').length, 3,
            "should still have 3 cells: 1 for the open header, and 2 for data");
        assert.strictEqual(pivot.$('.o_pivot_measure_row:contains(Foo)').length, 1,
            "should still have 1 row for measure Foo");
        pivot.destroy();
    });

    QUnit.test('can be grouped with the update function', function (assert) {
        assert.expect(4);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        assert.strictEqual(pivot.$('.o_pivot_cell_value').length, 1,
            "should have only 1 cell");
        assert.strictEqual(pivot.$('tbody tr').length, 1,
            "should have 1 rows");

        pivot.update({groupBy: ['product_id']});

        assert.strictEqual(pivot.$('.o_pivot_cell_value').length, 3,
            "should have 3 cells");
        assert.strictEqual(pivot.$('tbody tr').length, 3,
            "should have 3 rows");
        pivot.destroy();
    });

    QUnit.test('can sort data in a column by clicking on header', function (assert) {
        assert.expect(3);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="foo" type="measure"/>' +
                        '<field name="product_id" type="row"/>' +
                '</pivot>',
        });

        assert.strictEqual($('td.o_pivot_cell_value').text(), "321220",
            "should have proper values in cells (total, result 1, result 2");

        pivot.$('th.o_pivot_measure_row').click();

        assert.strictEqual($('td.o_pivot_cell_value').text(), "322012",
            "should have proper values in cells (total, result 2, result 1");

        pivot.$('th.o_pivot_measure_row').click();

        assert.strictEqual($('td.o_pivot_cell_value').text(), "321220",
            "should have proper values in cells (total, result 1, result 2");

        pivot.destroy();
    });

    QUnit.test('can expand all rows', function (assert) {
        assert.expect(7);

        var nbReadGroups = 0;
        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="foo" type="measure"/>' +
                        '<field name="product_id" type="row"/>' +
                '</pivot>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    nbReadGroups++;
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(nbReadGroups, 2, "should have done 2 read_group RPCS");
        assert.strictEqual(pivot.$('td.o_pivot_cell_value').text(), "321220",
            "should have proper values in cells (total, result 1, result 2)");

        // expand on date:days, product
        nbReadGroups = 0;
        pivot.update({groupBy: ['date:days', 'product_id']});

        assert.strictEqual(nbReadGroups, 3, "should have done 3 read_group RPCS");
        assert.strictEqual(pivot.$('tbody tr').length, 8,
            "should have 7 rows (total + 3 for December and 2 for October and April)");

        // collapse the last two rows
        pivot.$('.o_pivot_header_cell_opened').last().click();
        pivot.$('.o_pivot_header_cell_opened').last().click();

        assert.strictEqual(pivot.$('tbody tr').length, 6,
            "should have 6 rows now");

        // expand all
        nbReadGroups = 0;
        pivot.$buttons.find('.o_pivot_expand_button').click();

        assert.strictEqual(nbReadGroups, 3, "should have done 3 read_group RPCS");
        assert.strictEqual(pivot.$('tbody tr').length, 8,
            "should have 8 rows again");

        pivot.destroy();
    });

    QUnit.test('expand all with a delay', function (assert) {
        assert.expect(3);

        var def;
        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="foo" type="measure"/>' +
                        '<field name="product_id" type="row"/>' +
                '</pivot>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'read_group') {
                    return $.when(def).then(_.constant(result));
                }
                return result;
            },
        });

        // expand on date:days, product
        pivot.update({groupBy: ['date:days', 'product_id']});

        assert.strictEqual(pivot.$('tbody tr').length, 8,
            "should have 7 rows (total + 3 for December and 2 for October and April)");

        // collapse the last two rows
        pivot.$('.o_pivot_header_cell_opened').last().click();
        pivot.$('.o_pivot_header_cell_opened').last().click();

        assert.strictEqual(pivot.$('tbody tr').length, 6,
            "should have 6 rows now");

        // expand all
        def = $.Deferred();
        pivot.$buttons.find('.o_pivot_expand_button').click();
        def.resolve();

        assert.strictEqual(pivot.$('tbody tr').length, 8,
            "should have 8 rows again");

        pivot.destroy();
    });

    QUnit.test('can download a file', function (assert) {
        assert.expect(1);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="date" interval="month" type="col"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
            session: {
                get_file: function (args) {
                    assert.strictEqual(args.url, '/web/pivot/export_xls',
                        "should call get_file with correct parameters");
                    args.complete();
                },
            },
        });

        pivot.$buttons.find('.o_pivot_download').click();
        pivot.destroy();
    });

    QUnit.test('can download a file without data', function (assert) {
        assert.expect(1);

        this.data.partner.records = [];

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="date" interval="month" type="col"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
            session: {
                get_file: function (args) {
                    assert.strictEqual(args.url, '/web/pivot/export_xls',
                        "should call get_file with correct parameters");
                    args.complete();
                },
            },
        });

        pivot.$buttons.find('.o_pivot_download').click();
        pivot.destroy();
    });

    QUnit.test('getContext correctly returns measures and groupbys', function (assert) {
        assert.expect(3);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="date" interval="day" type="col"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        assert.deepEqual(pivot.getContext(), {
            pivot_column_groupby: ['date:day'],
            pivot_measures: ['foo'],
            pivot_row_groupby: [],
        }, "context should be correct");

        // expand header on field customer
        pivot.$('thead .o_pivot_header_cell_closed:nth(1)').click();
        pivot.$('.o_pivot_field_menu .dropdown-item[data-field="customer"]:first').click();
        assert.deepEqual(pivot.getContext(), {
            pivot_column_groupby: ['date:day', 'customer'],
            pivot_measures: ['foo'],
            pivot_row_groupby: [],
        }, "context should be correct");

        // expand row on field product_id
        pivot.$('tbody .o_pivot_header_cell_closed').first().click();
        pivot.$('.o_pivot_field_menu .dropdown-item[data-field="product_id"]:first').click();
        assert.deepEqual(pivot.getContext(), {
            pivot_column_groupby: ['date:day', 'customer'],
            pivot_measures: ['foo'],
            pivot_row_groupby: ['product_id'],
        }, "context should be correct");

        pivot.destroy();
    });

    QUnit.test('correctly uses pivot_ keys from the context', function (assert) {
        assert.expect(7);

        this.data.partner.fields.amount = {string: "Amount", type: "float"};

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="date" interval="day" type="col"/>' +
                        '<field name="amount" type="measure"/>' +
                '</pivot>',
            viewOptions: {
                context: {
                    pivot_measures: ['foo'],
                    pivot_column_groupby: ['customer'],
                    pivot_row_groupby: ['product_id'],
                },
            },
        });

        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_opened').length, 1,
            "column: should have one opened header");
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed:contains(First)').length, 1,
            "column: should display one closed header with 'First'");
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed:contains(Second)').length, 1,
            "column: should display one closed header with 'Second'");

        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_opened').length, 1,
            "row: should have one opened header");
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xphone)').length, 1,
            "row: should display one closed header with 'xphone'");
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xpad)').length, 1,
            "row: should display one closed header with 'xpad'");

        assert.strictEqual(pivot.$('tbody tr:first td:nth(3)').text(), '32',
            "selected measure should be foo, with total 32");

        pivot.destroy();
    });

    QUnit.test('correctly uses pivot_ keys from the context (at reload)', function (assert) {
        assert.expect(8);

        this.data.partner.fields.amount = {string: "Amount", type: "float"};

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="date" interval="day" type="col"/>' +
                        '<field name="amount" type="measure"/>' +
                '</pivot>',
        });

        assert.strictEqual(pivot.$('tbody tr:first td.o_pivot_cell_value:last').text(), '0.00',
            "the active measure should be amount");

        var reloadParams = {
            context: {
                pivot_measures: ['foo'],
                pivot_column_groupby: ['customer'],
                pivot_row_groupby: ['product_id'],
            },
        };
        pivot.reload(reloadParams);

        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_opened').length, 1,
            "column: should have one opened header");
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed:contains(First)').length, 1,
            "column: should display one closed header with 'First'");
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed:contains(Second)').length, 1,
            "column: should display one closed header with 'Second'");

        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_opened').length, 1,
            "row: should have one opened header");
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xphone)').length, 1,
            "row: should display one closed header with 'xphone'");
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xpad)').length, 1,
            "row: should display one closed header with 'xpad'");

        assert.strictEqual(pivot.$('tbody tr:first td:nth(3)').text(), '32',
            "selected measure should be foo, with total 32");

        pivot.destroy();
    });

    QUnit.test('correctly use group_by key from the context', function (assert) {
        assert.expect(7);

        var pivot = createView({
            View: PivotView,
            model: 'partner',
            data: this.data,
            arch: '<pivot>' +
                        '<field name="customer" type="col" />' +
                        '<field name="foo" type="measure" />' +
                '</pivot>',
            groupBy: ['product_id'],
        });

        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_opened').length, 1,
            'column: should have one opened header');
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed:contains(First)').length, 1,
            'column: should display one closed header with "First"');
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed:contains(Second)').length, 1,
            'column: should display one closed header with "Second"');

        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_opened').length, 1,
            'row: should have one opened header');
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xphone)').length, 1,
            'row: should display one closed header with "xphone"');
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xpad)').length, 1,
            'row: should display one closed header with "xpad"');

        assert.strictEqual(pivot.$('tbody tr:first td:nth(3)').text(), '32',
            'selected measure should be foo, with total 32');

        pivot.destroy();
    });

    QUnit.test('pivot still handles __count__ measure', function (assert) {
        // for retro-compatibility reasons, the pivot view still handles
        // '__count__' measure.
        assert.expect(2);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot></pivot>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.fields, ['__count'],
                        "should make a read_group with field __count");
                }
                return this._super(route, args);
            },
            viewOptions: {
                context: {
                    pivot_measures: ['__count__'],
                },
            },
        });

        var $countMeasure = pivot.$buttons.find('.dropdown-item[data-field=__count]:first');
        assert.ok($countMeasure.hasClass('selected'), "The count measure should be activated");

        pivot.destroy();
    });

    QUnit.test('not use a many2one as a measure by default', function (assert) {
        assert.expect(1);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id"/>' +
                        '<field name="date" interval="month" type="col"/>' +
                '</pivot>',
        });
        assert.notOk(pivot.measures.product_id,
            "should not have product_id as measure");
        pivot.destroy();
    });

    QUnit.test('use a many2one as a measure with specified additional measure', function (assert) {
        assert.expect(1);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id"/>' +
                        '<field name="date" interval="month" type="col"/>' +
                '</pivot>',
            viewOptions: {
                additionalMeasures: ['product_id'],
            },
        });
        assert.ok(pivot.measures.product_id,
            "should have product_id as measure");
        pivot.destroy();
    });

    QUnit.test('pivot view with many2one field as a measure', function (assert) {
        assert.expect(1);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="measure"/>' +
                        '<field name="date" interval="month" type="col"/>' +
                '</pivot>',
        });

        assert.strictEqual(pivot.$('table tbody tr').text().trim(), "Total2112",
            "should display product_id count as measure");
        pivot.destroy();
    });

    QUnit.test('m2o as measure, drilling down into data', function (assert) {
        assert.expect(1);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="measure"/>' +
                '</pivot>',
        });
        pivot.$('tbody .o_pivot_header_cell_closed').first().click();
        // click on date by month
        pivot.$('.o_pivot_field_menu .dropdown-item[data-field="date"][data-interval="month"]').click();

        assert.strictEqual(pivot.$('.o_pivot_cell_value').text(), '2211',
            'should have loaded the proper data');
        pivot.destroy();
    });

    QUnit.test('pivot view with same many2one field as a measure and grouped by', function (assert) {
        assert.expect(1);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="row"/>' +
                '</pivot>',
            viewOptions: {
                additionalMeasures: ['product_id'],
            },
        });

        pivot.$buttons.find('.dropdown-item[data-field=product_id]:first').click();
        assert.strictEqual(pivot.$('.o_pivot_cell_value').text(), '421131',
            'should have loaded the proper data');
        pivot.destroy();
    });

    QUnit.test('pivot view with same many2one field as a measure and grouped by (and drill down)', function (assert) {
        assert.expect(1);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="measure"/>' +
                '</pivot>',
        });

        pivot.$('tbody .o_pivot_header_cell_closed').first().click();

        pivot.$('.o_pivot_field_menu .dropdown-item[data-field="product_id"]:first').click();

        assert.strictEqual(pivot.$('.o_pivot_cell_value').text(), '211',
            'should have loaded the proper data');
        pivot.destroy();
    });

    QUnit.test('Row and column groupbys plus a domain', function (assert) {
        assert.expect(3);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        // Set a column groupby
        pivot.$('thead .o_pivot_header_cell_closed').click();
        pivot.$('.o_field_selection .dropdown-item[data-field=customer]:first').click();

        // Set a Row groupby
        pivot.$('tbody .o_pivot_header_cell_closed').click();
        pivot.$('.o_pivot_field_menu .dropdown-item[data-field=product_id]:first').click();

        // Set a domain
        pivot.update({domain: [['product_id', '=', 41]]});

        var expectedContext = {pivot_column_groupby: ['customer'],
                               pivot_measures: ['foo'],
                               pivot_row_groupby: ['product_id']};

        // Mock 'save as favorite'
        assert.deepEqual(pivot.getContext(), expectedContext,
            'The pivot view should have the right context');

        var $xpadHeader = pivot.$('tbody .o_pivot_header_cell_closed[data-original-title=Product]');
        assert.equal($xpadHeader.length, 1,
            'There should be only one product line because of the domain');

        assert.equal($xpadHeader.text(), 'xpad',
            'The product should be the right one');

        pivot.destroy();
    });

    QUnit.test('parallel data loading should discard all but the last one', function (assert) {
        assert.expect(2);

        var def;

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                      '<field name="foo" type="measure"/>' +
                  '</pivot>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'read_group') {
                    return $.when(def).then(_.constant(result));
                }
                return result;
            },
        });

        def = $.Deferred();
        pivot.update({groupBy: ['product_id']});
        pivot.update({groupBy: ['product_id', 'customer']});
        def.resolve();

        assert.strictEqual(pivot.$('.o_pivot_cell_value').length, 6,
            "should have 6 cells");
        assert.strictEqual(pivot.$('tbody tr').length, 6,
            "should have 6 rows");
        pivot.destroy();
    });

    QUnit.test('pivot measures should be alphabetically sorted', function (assert) {
        assert.expect(2);

        var data = this.data;
        data.partner.fields.bouh = {string: "bouh", type: "integer"};

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: data,
            arch: '<pivot>' +
                        '<field name="foo" type="measure"/>' +
                        '<field name="bouh" type="measure"/>' +
                  '</pivot>',
        })

        assert.strictEqual(pivot.$buttons.find('.o_pivot_measures_list .dropdown-item:first').data('field'), 'bouh',
            "Bouh should be the first measure");
        assert.strictEqual(pivot.$buttons.find('.o_pivot_measures_list .dropdown-item:last').data('field'), '__count',
            "Count should be the last measure");

        pivot.destroy();
    });

    QUnit.test('pivot view should use default order for auto sorting', function (assert) {
        assert.expect(1);

        var pivot = createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot default_order="foo asc">' +
                        '<field name="foo" type="measure"/>' +
                  '</pivot>',
        });

        assert.ok(pivot.$('thead tr:last th:last').hasClass('o_pivot_measure_row_sorted_asc'),
                        "Last thead should be sorted in ascending order");

        pivot.destroy();
    });
});});
