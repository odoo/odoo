odoo.define('web.pivot_tests', function (require) {
"use strict";

var core = require('web.core');
var PivotView = require('web.PivotView');
var testUtils = require('web.test_utils');
var testUtilsDom = require('web.test_utils_dom');

var _t = core._t;
var createActionManager = testUtils.createActionManager;
var createView = testUtils.createView;
var patchDate = testUtils.mock.patchDate;

/**
 * Helper function that returns, given a pivot instance, the values of the
 * table, separated by ','.
 *
 * @returns {string}
 */
var getCurrentValues = function (pivot) {
    return pivot.$('.o_pivot_cell_value div').map(function () {
        return $(this).text();
    }).get().join();
};


QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "integer", searchable: true, group_operator: 'sum'},
                    bar: {string: "bar", type: "boolean", store: true, sortable: true},
                    date: {string: "Date", type: "date", store: true, sortable: true},
                    product_id: {string: "Product", type: "many2one", relation: 'product', store: true},
                    other_product_id: {string: "Other Product", type: "many2one", relation: 'product', store: true},
                    non_stored_m2o: {string: "Non Stored M2O", type: "many2one", relation: 'product'},
                    customer: {string: "Customer", type: "many2one", relation: 'customer', store: true},
                    computed_field: {string: "Computed and not stored", type: 'integer', compute: true, group_operator: 'sum'},
                    company_type: {
                        string: "Company Type", type: "selection",
                        selection: [["company", "Company"], ["individual", "individual"]],
                        searchable: true, sortable: true, store: true,
                    },
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
                        company_type: 'company',
                    }, {
                        id: 2,
                        foo: 1,
                        bar: true,
                        date: '2016-10-26',
                        product_id: 41,
                        customer: 2,
                        computed_field: 23,
                        company_type: 'individual',
                    }, {
                        id: 3,
                        foo: 17,
                        bar: true,
                        date: '2016-12-15',
                        product_id: 41,
                        customer: 2,
                        computed_field: 26,
                        company_type: 'company',
                    }, {
                        id: 4,
                        foo: 2,
                        bar: false,
                        date: '2016-04-11',
                        product_id: 41,
                        customer: 1,
                        computed_field: 19,
                        company_type: 'individual',
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

    QUnit.test('simple pivot rendering', async function (assert) {
        assert.expect(3);

        var pivot = await createView({
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

        assert.hasClass(pivot.$('table'), 'o_enable_linking',
            "table should have classname 'o_enable_linking'");
        assert.strictEqual(pivot.$('td.o_pivot_cell_value:contains(32)').length, 1,
                    "should contain a pivot cell with the sum of all records");
        pivot.destroy();
    });

    QUnit.test('pivot rendering with widget', async function (assert) {
        assert.expect(1);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners">' +
                        '<field name="foo" type="measure" widget="float_time"/>' +
                '</pivot>',
        });

        assert.strictEqual(pivot.$('td.o_pivot_cell_value:contains(32:00)').length, 1,
                    "should contain a pivot cell with the sum of all records");
        pivot.destroy();
    });

    QUnit.test('pivot rendering with string attribute on field', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.foo = {string: "Foo", type: "integer", store: true, group_operator: 'sum'};

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners">' +
                        '<field name="foo" string="BAR" type="measure"/>' +
                '</pivot>',
        });

        assert.strictEqual(pivot.$('.o_pivot_measure_row').text(), "BAR",
                    "the displayed name should be the one set in the string attribute");
        pivot.destroy();
    });

    QUnit.test('pivot rendering with string attribute on non stored field', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.fubar = {string: "Fubar", type: "integer", store: false, group_operator: 'sum'};

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners">' +
                        '<field name="fubar" string="fubar" type="measure"/>' +
                '</pivot>',
        });
        assert.containsOnce(pivot, '.o_pivot', 'Non stored fields can have a string attribute');
        pivot.destroy();
    });

    QUnit.test('pivot rendering with invisible attribute on field', async function (assert) {
        assert.expect(2);
        // when invisible, a field should neither be an active measure,
        // nor be a selectable measure.
        _.extend(this.data.partner.fields, {
            foo: {string: "Foo", type: "integer", store: true, group_operator: 'sum'},
            foo2: {string: "Foo2", type: "integer", store: true, group_operator: 'sum'}
        });

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners">' +
                        '<field name="foo" type="measure"/>' +
                        '<field name="foo2" type="measure" invisible="True"/>' +
                '</pivot>',
        });

        // there should be only one displayed measure as the other one is invisible
        assert.containsOnce(pivot, '.o_pivot_measure_row');
        // there should be only one measure besides count, as the other one is invisible
        assert.containsN(pivot, '.o_cp_left .dropdown-item', 2);

        pivot.destroy();
    });

    QUnit.test('pivot view without "string" attribute', async function (assert) {
        assert.expect(1);

        var pivot = await createView({
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

    QUnit.test('group headers should have a tooltip', async function (assert) {
        assert.expect(2);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="col"/>' +
                        '<field name="date" type="row"/>' +
                '</pivot>',
        });

        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:first').attr('data-original-title'), 'Date');
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed:first').attr('data-original-title'), 'Product');

        pivot.destroy();
    });

    QUnit.test('pivot view add computed fields explicitly defined as measure', async function (assert) {
        assert.expect(1);

        var pivot = await createView({
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

    QUnit.test('clicking on a cell triggers a do_action', async function (assert) {
        assert.expect(2);

        var pivot = await createView({
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

        assert.hasClass(pivot.$('table'), 'o_enable_linking',
            "table should have classname 'o_enable_linking'");
        await testUtils.dom.click(pivot.$('.o_pivot_cell_value:contains(12)')); // should trigger a do_action

        pivot.destroy();
    });

    QUnit.test('row and column are highlighted when hovering a cell', async function (assert) {
        assert.expect(11);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners">' +
                        '<field name="foo" type="col"/>' +
                        '<field name="product_id" type="row"/>' +
                '</pivot>',
        });

        // check row highlighting
        assert.hasClass(pivot.$('table'), 'table-hover',
            "with className 'table-hover', rows are highlighted (bootstrap)");

        // check column highlighting
        // hover third measure
        await testUtils.dom.triggerEvents(pivot.$('th.o_pivot_measure_row:nth(2)'), 'mouseenter');
        assert.containsN(pivot, '.o_cell_hover', 3);
        for (var i = 0; i < 3; i++) {
            assert.hasClass(pivot.$('tbody tr:nth(' + i + ') td:nth(2)'), 'o_cell_hover');
        }
        await testUtils.dom.triggerEvents(pivot.$('th.o_pivot_measure_row:nth(2)'), 'mouseleave');
        assert.containsNone(pivot, '.o_cell_hover');

        // hover second cell, second row
        await testUtils.dom.triggerEvents(pivot.$('tbody tr:nth(1) td:nth(1)'), 'mouseenter');
        assert.containsN(pivot, '.o_cell_hover', 3);
        for (i = 0; i < 3; i++) {
            assert.hasClass(pivot.$('tbody tr:nth(' + i + ') td:nth(1)'), 'o_cell_hover');
        }
        await testUtils.dom.triggerEvents(pivot.$('tbody tr:nth(1) td:nth(1)'), 'mouseleave');
        assert.containsNone(pivot, '.o_cell_hover');

        pivot.destroy();
    });

    QUnit.test('pivot view with disable_linking="True"', async function (assert) {
        assert.expect(2);

        var pivot = await createView({
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

        assert.doesNotHaveClass(pivot.$('table'), 'o_enable_linking',
            "table should not have classname 'o_enable_linking'");
        assert.containsOnce(pivot, '.o_pivot_cell_value',
            "should have one cell");
        await testUtils.dom.click(pivot.$('.o_pivot_cell_value')); // should not trigger a do_action

        pivot.destroy();
    });

    QUnit.test('clicking on the "Total" Cell with time range activated gives the right action domain', async function (assert) {
        assert.expect(2);

        var unpatchDate = patchDate(2016, 11, 20, 1, 0, 0);
        var context = {
            timeRangeMenuData: {
                timeRange: ["&",["date",">=","2016-12-01"],["date","<","2017-01-01"]],
                timeRangeDescription: 'This Month',
                comparisonTimeRange: [],
            }
        };
        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot/>',
            intercepts: {
                do_action: function (ev) {
                    assert.deepEqual(
                        ev.data.action.domain,
                        ["&",["date",">=","2016-12-01"],["date","<","2017-01-01"]],
                        "should trigger do_action with the correct action domain"
                    );
                },
            },
            viewOptions: {
                context: context,
                title: 'Partners',
            }
        });

        assert.hasClass(pivot.$('table'), 'o_enable_linking',
            "root node should have classname 'o_enable_linking'");
        await testUtilsDom.click(pivot.$('.o_pivot_cell_value'));

        unpatchDate();
        pivot.destroy();
    });

    QUnit.test('clicking on a fake cell value ("empty group") in comparison mode gives an action domain equivalent to [[0,"=",1]]', async function (assert) {
        assert.expect(3);

        var unpatchDate = patchDate(2016, 11, 20, 1, 0, 0);

        this.data.partner.records[0].date = '2016-11-15';
        this.data.partner.records[1].date = '2016-11-17';
        this.data.partner.records[2].date = '2016-11-22';
        this.data.partner.records[3].date = '2016-11-03';

        var context = {
            timeRangeMenuData: {
                timeRange: ["&",["date",">=","2016-12-01"],["date","<","2017-01-01"]],
                timeRangeDescription: 'This Month',
                comparisonTimeRange: ["&",["date",">=","2016-11-01"],["date","<","2017-12-01"]],
                comparisonTimeRangeDescription: 'Previous Period'
            }
        };

        var first_do_action = true;
        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="row"/>' +
                    '</pivot>',
            intercepts: {
                do_action: function (ev) {
                    if (first_do_action) {
                        assert.deepEqual(
                            ev.data.action.domain,
                            ["&",["date",">=","2016-12-01"],["date","<","2017-01-01"]],
                            "should trigger do_action with the correct action domain"
                        );
                    } else {
                        assert.deepEqual(
                            ev.data.action.domain,
                            [[0, "=", 1]],
                            "should trigger do_action with the correct action domain"
                        );
                    }
                    first_do_action = false;
                },
            },
            viewOptions: {
                context: context,
                title: 'Partners',
            }
        });
        assert.hasClass(pivot.$('table'), 'o_enable_linking',
            "root node should have classname 'o_enable_linking'");
        // here we click on the group corresponding to Total/Total/This Month
        pivot.$('.o_pivot_cell_value').eq(0).click(); // should trigger a do_action with appropriate domain
        // here we click on the group corresponding to xphone/Total/This Month
        pivot.$('.o_pivot_cell_value').eq(3).click(); // should trigger a do_action with appropriate domain

        unpatchDate();
        pivot.destroy();
    });

    QUnit.test('pivot view grouped by date field', async function (assert) {
        assert.expect(2);

        var data = this.data;
        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="date" interval="month" type="col"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
            mockRPC: function (route, params) {
                var wrong_fields = _.filter(params.kwargs.fields, function (field) {
                    return !(field.split(':')[0] in data.partner.fields);
                });
                assert.ok(!wrong_fields.length, 'fields given to read_group should exist on the model');
                return this._super.apply(this, arguments);
            },
        });
        pivot.destroy();
    });

    QUnit.test('without measures, pivot view uses __count by default', async function (assert) {
        assert.expect(2);

        var pivot = await createView({
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
        assert.hasClass($countMeasure, 'selected', "The count measure should be activated");
        pivot.destroy();
    });

    QUnit.test('pivot view can be reloaded', async function (assert) {
        assert.expect(4);
        var readGroupCount = 0;

        var pivot = await createView({
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

        await testUtils.pivot.reload(pivot, {domain: [['foo', '>', 10]]});
        assert.strictEqual(pivot.$('td.o_pivot_cell_value:contains(2)').length, 1,
                    "should contain a pivot cell with the number of remaining records");
        assert.strictEqual(readGroupCount, 2, "should have done 2 rpcs");
        pivot.destroy();
    });

    QUnit.test('pivot view grouped by many2one field', async function (assert) {
        assert.expect(3);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="row"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        assert.containsOnce(pivot, '.o_pivot_header_cell_opened',
            "should have one opened header");
        assert.strictEqual(pivot.$('.o_pivot_header_cell_closed:contains(xphone)').length, 1,
            "should display one header with 'xphone'");
        assert.strictEqual(pivot.$('.o_pivot_header_cell_closed:contains(xpad)').length, 1,
            "should display one header with 'xpad'");
        pivot.destroy();
    });

    QUnit.test('basic folding/unfolding', async function (assert) {
        assert.expect(7);

        var rpcCount = 0;

        var pivot = await createView({
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

        assert.containsN(pivot, 'tbody tr', 3,
            "should have 3 rows: 1 for the opened header, and 2 for data");

        // click on the opened header to close it
        await testUtils.dom.click(pivot.$('.o_pivot_header_cell_opened'));

        assert.containsOnce(pivot, 'tbody tr', "should have 1 row");

        // click on closed header to open dropdown
        await testUtils.dom.click(pivot.$('tbody .o_pivot_header_cell_closed'));
        assert.containsN(pivot, '.o_pivot_field_menu .dropdown-item[data-field="date"]', 6,
            "should have the date field as proposition (Date, Day, Week, Month, Quarter and Year)");
        assert.containsOnce(pivot, '.o_field_selection .dropdown-item[data-field="product_id"]',
            "should have the product_id field as proposition");
        assert.containsNone(pivot, '.o_field_selection .dropdown-item[data-field="non_stored_m2o"]:first',
            "should not have the non_stored_m2o field as proposition");

        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field="date"]:first'));

        assert.containsN(pivot, 'tbody tr', 4,
            "should have 4 rows: one for header, 3 for data");
        assert.strictEqual(rpcCount, 3,
            "should have done 3 rpcs (initial load) + open header with different groupbys");

        pivot.destroy();
    });

    QUnit.test('more folding/unfolding', async function (assert) {
        assert.expect(1);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="row"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        // open dropdown to zoom into first row
        await testUtils.dom.clickFirst(pivot.$('tbody .o_pivot_header_cell_closed'));
        // click on date by day
        pivot.$('.dropdown-menu.show .o_inline_dropdown .dropdown-menu').toggle(); // unfold inline dropdown
        await testUtils.nextTick();
        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field="date"][data-interval="day"]'));

        // open dropdown to zoom into second row
        await testUtils.dom.clickLast(pivot.$('tbody th.o_pivot_header_cell_closed'));

        assert.containsN(pivot, 'tbody tr', 7,
            "should have 7 rows (1 for total, 1 for xphone, 1 for xpad, 4 for data)");

        pivot.destroy();
    });

    QUnit.test('fold and unfold header group', async function (assert) {
        assert.expect(3);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="col"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        assert.containsN(pivot, 'thead tr', 3);

        // fold opened col group
        await testUtils.dom.click(pivot.$('thead .o_pivot_header_cell_opened'));
        assert.containsN(pivot, 'thead tr', 2);

        // unfold it
        await testUtils.dom.click(pivot.$('thead .o_pivot_header_cell_closed'));
        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field="product_id"]'));
        assert.containsN(pivot, 'thead tr', 3);

        pivot.destroy();
    });

    QUnit.test('unfold second header group', async function (assert) {
        assert.expect(4);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="col"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        assert.containsN(pivot, 'thead tr', 3);
        var values = ['12', '20', '32'];
        assert.strictEqual(getCurrentValues(pivot), values.join(','));

        // unfold it
        await testUtils.dom.click(pivot.$('thead .o_pivot_header_cell_closed:nth(1)'));
        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field="company_type"]'));
        assert.containsN(pivot, 'thead tr', 4);
        values = ['12', '3', '17', '32'];
        assert.strictEqual(getCurrentValues(pivot), values.join(','));

        pivot.destroy();
    });

    QUnit.test('can toggle extra measure', async function (assert) {
        assert.expect(8);

        var rpcCount = 0;

        var pivot = await createView({
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

        assert.containsN(pivot, '.o_pivot_cell_value', 3,
            "should have 3 cells: 1 for the open header, and 2 for data");
        assert.doesNotHaveClass(pivot.$buttons.find('.dropdown-item[data-field=__count]:first'), 'selected',
            "the __count measure should not be selected");

        rpcCount = 0;
        await testUtils.pivot.toggleMeasuresDropdown(pivot);
        await testUtils.pivot.clickMeasure(pivot, '__count');

        assert.hasClass(pivot.$buttons.find('.dropdown-item[data-field=__count]:first'), 'selected',
            "the __count measure should be selected");
        assert.containsN(pivot, '.o_pivot_cell_value', 6,
            "should have 6 cells: 2 for the open header, and 4 for data");
        assert.strictEqual(rpcCount, 2,
            "should have done 2 rpcs to reload data");

        await testUtils.pivot.clickMeasure(pivot, '__count');

        assert.doesNotHaveClass(pivot.$buttons.find('.dropdown-item[data-field=__count]:first'), 'selected',
            "the __count measure should not be selected");
        assert.containsN(pivot, '.o_pivot_cell_value', 3,
            "should have 3 cells: 1 for the open header, and 2 for data");
        assert.strictEqual(rpcCount, 2,
            "should not have done any extra rpcs");

        pivot.destroy();
    });

    QUnit.test('no content helper when no active measure', async function (assert) {
        assert.expect(4);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners">' +
                '</pivot>',
        });

        assert.containsNone(pivot, '.o_view_nocontent',
            "should not have a no_content_helper");
        assert.containsOnce(pivot, 'table',
            "should have a table in DOM");

        await testUtils.pivot.toggleMeasuresDropdown(pivot);
        await testUtils.pivot.clickMeasure(pivot, '__count');

        assert.containsOnce(pivot, '.o_view_nocontent',
            "should have a no_content_helper");
        assert.containsNone(pivot, 'table',
            "should not have a table in DOM");
        pivot.destroy();
    });

    QUnit.test('no content helper when no data', async function (assert) {
        assert.expect(4);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners">' +
                '</pivot>',
        });

        assert.containsNone(pivot, '.o_view_nocontent',
            "should not have a no_content_helper");
        assert.containsOnce(pivot, 'table',
            "should have a table in DOM");

        await testUtils.pivot.reload(pivot, {domain: [['foo', '=', 12345]]});

        assert.containsOnce(pivot, '.o_view_nocontent',
            "should have a no_content_helper");
        assert.containsNone(pivot, 'table',
            "should not have a table in DOM");
        pivot.destroy();
    });

    QUnit.test('no content helper when no data, part 2', async function (assert) {
        assert.expect(1);

        this.data.partner.records = [];

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners"></pivot>',
        });

        assert.containsOnce(pivot, '.o_view_nocontent',
            "should have a no_content_helper");
        pivot.destroy();
    });

    QUnit.test('no content helper when no data, part 3', async function (assert) {
        assert.expect(4);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot string="Partners"></pivot>',
            viewOptions: {
                domain: [['foo', '=', 12345]]
            },
        });

        assert.containsOnce(pivot, '.o_view_nocontent',
            "should have a no_content_helper");
        await testUtils.pivot.reload(pivot, {domain: [['foo', '=', 12345]]});
        assert.containsOnce(pivot, '.o_view_nocontent',
            "should still have a no_content_helper");
        await testUtils.pivot.reload(pivot, {domain: []});
        assert.containsNone(pivot, '.o_view_nocontent',
            "should not have a no_content_helper");

        // tries to open a field selection menu, to make sure it was not
        // removed from the dom.
        await testUtils.dom.clickFirst(pivot.$('.o_pivot_header_cell_closed'));
        assert.containsOnce(pivot, '.o_pivot_field_menu',
            "the field selector menu exists");
        pivot.destroy();
    });

    QUnit.test('tries to restore previous state after domain change', async function (assert) {
        assert.expect(5);

        var rpcCount = 0;

        var pivot = await createView({
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

        assert.containsN(pivot, '.o_pivot_cell_value', 3,
            "should have 3 cells: 1 for the open header, and 2 for data");
        assert.strictEqual(pivot.$('.o_pivot_measure_row:contains(Foo)').length, 1,
            "should have 1 row for measure Foo");

        await testUtils.pivot.reload(pivot, {domain: [['foo', '=', 12345]]});

        rpcCount = 0;
        await testUtils.pivot.reload(pivot, {domain: []});

        assert.equal(rpcCount, 2, "should have reloaded data");
        assert.containsN(pivot, '.o_pivot_cell_value', 3,
            "should still have 3 cells: 1 for the open header, and 2 for data");
        assert.strictEqual(pivot.$('.o_pivot_measure_row:contains(Foo)').length, 1,
            "should still have 1 row for measure Foo");
        pivot.destroy();
    });

    QUnit.test('can be grouped with the update function', async function (assert) {
        assert.expect(4);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        assert.containsOnce(pivot, '.o_pivot_cell_value',
            "should have only 1 cell");
        assert.containsOnce(pivot, 'tbody tr',
            "should have 1 rows");

        await testUtils.pivot.reload(pivot, {groupBy: ['product_id']});

        assert.containsN(pivot, '.o_pivot_cell_value', 3,
            "should have 3 cells");
        assert.containsN(pivot, 'tbody tr', 3,
            "should have 3 rows");
        pivot.destroy();
    });

    QUnit.test('can sort data in a column by clicking on header', async function (assert) {
        assert.expect(3);

        var pivot = await createView({
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

        await testUtils.dom.click(pivot.$('th.o_pivot_measure_row'));

        assert.strictEqual($('td.o_pivot_cell_value').text(), "321220",
            "should have proper values in cells (total, result 1, result 2");

        await testUtils.dom.click(pivot.$('th.o_pivot_measure_row'));

        assert.strictEqual($('td.o_pivot_cell_value').text(), "322012",
            "should have proper values in cells (total, result 2, result 1");

        pivot.destroy();
    });

    QUnit.test('can expand all rows', async function (assert) {
        assert.expect(7);

        var nbReadGroups = 0;
        var pivot = await createView({
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
        await testUtils.pivot.reload(pivot, {groupBy: ['date:days', 'product_id']});

        assert.strictEqual(nbReadGroups, 3, "should have done 3 read_group RPCS");
        assert.containsN(pivot, 'tbody tr', 8,
            "should have 7 rows (total + 3 for December and 2 for October and April)");

        // collapse the last two rows
        await testUtils.dom.clickLast(pivot.$('.o_pivot_header_cell_opened'));
        await testUtils.dom.clickLast(pivot.$('.o_pivot_header_cell_opened'));

        assert.containsN(pivot, 'tbody tr', 6,
            "should have 6 rows now");

        // expand all
        nbReadGroups = 0;
        await testUtils.dom.click(pivot.$buttons.find('.o_pivot_expand_button'));

        assert.strictEqual(nbReadGroups, 3, "should have done 3 read_group RPCS");
        assert.containsN(pivot, 'tbody tr', 8,
            "should have 8 rows again");

        pivot.destroy();
    });

    QUnit.test('expand all with a delay', async function (assert) {
        assert.expect(3);

        var def;
        var pivot = await createView({
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
                    return Promise.resolve(def).then(_.constant(result));
                }
                return result;
            },
        });

        // expand on date:days, product
        await testUtils.pivot.reload(pivot, {groupBy: ['date:days', 'product_id']});

        assert.containsN(pivot, 'tbody tr', 8,
            "should have 7 rows (total + 3 for December and 2 for October and April)");

        // collapse the last two rows
        await testUtils.dom.clickLast(pivot.$('.o_pivot_header_cell_opened'));
        await testUtils.dom.clickLast(pivot.$('.o_pivot_header_cell_opened'));

        assert.containsN(pivot, 'tbody tr', 6,
            "should have 6 rows now");

        // expand all
        def = testUtils.makeTestPromise();
        await testUtils.dom.click(pivot.$buttons.find('.o_pivot_expand_button'));
        def.resolve();
        await testUtils.nextTick();
        assert.containsN(pivot, 'tbody tr', 8,
            "should have 8 rows again");

        pivot.destroy();
    });

    QUnit.test('can download a file', async function (assert) {
        assert.expect(1);

        var pivot = await createView({
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

        await testUtils.dom.click(pivot.$buttons.find('.o_pivot_download'));
        pivot.destroy();
    });

    QUnit.test('download button is disabled when there is no data', async function (assert) {
        assert.expect(1);

        this.data.partner.records = [];

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="date" interval="month" type="col"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        assert.hasAttrValue(pivot.$buttons.find('.o_pivot_download'), 'disabled', 'disabled',
            "download button should be disabled");
        pivot.destroy();
    });

    QUnit.test('getOwnedQueryParams correctly returns measures and groupbys', async function (assert) {
        assert.expect(3);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="date" interval="day" type="col"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        assert.deepEqual(pivot.getOwnedQueryParams(), {
            context: {
                pivot_column_groupby: ['date:day'],
                pivot_measures: ['foo'],
                pivot_row_groupby: [],
            },
        }, "context should be correct");

        // expand header on field customer
        await testUtils.dom.click(pivot.$('thead .o_pivot_header_cell_closed:nth(1)'));
        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field="customer"]:first'));
        assert.deepEqual(pivot.getOwnedQueryParams(), {
            context: {
                pivot_column_groupby: ['date:day', 'customer'],
                pivot_measures: ['foo'],
                pivot_row_groupby: [],
            },
        }, "context should be correct");

        // expand row on field product_id
        await testUtils.dom.click(pivot.$('tbody .o_pivot_header_cell_closed'));
        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field="product_id"]:first'));
        assert.deepEqual(pivot.getOwnedQueryParams(), {
            context: {
                pivot_column_groupby: ['date:day', 'customer'],
                pivot_measures: ['foo'],
                pivot_row_groupby: ['product_id'],
            },
        }, "context should be correct");

        pivot.destroy();
    });

    QUnit.test('correctly remove pivot_ keys from the context', async function (assert) {
        assert.expect(5);

        this.data.partner.fields.amount = {string: "Amount", type: "float", group_operator: 'sum'};

        // Equivalent to loading with default filter
        var pivot = await createView({
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

        // Equivalent to unload the filter
        var reloadParams = {
            context: {},
        };
        await pivot.reload(reloadParams);

        assert.deepEqual(pivot.getOwnedQueryParams(), {
            context: {
                pivot_column_groupby: ['customer'],
                pivot_measures: ['foo'],
                pivot_row_groupby: ['product_id'],
            },
        }, "context should be correct");

        // Let's get rid of the rows groupBy
        await testUtils.dom.click(pivot.$('tbody .o_pivot_header_cell_opened'));

        assert.deepEqual(pivot.getOwnedQueryParams(), {
            context: {
                pivot_column_groupby: ['customer'],
                pivot_measures: ['foo'],
                pivot_row_groupby: [],
            },
        }, "context should be correct");

        // And now, get rid of the col groupby
        await testUtils.dom.click(pivot.$('thead .o_pivot_header_cell_opened'));

        assert.deepEqual(pivot.getOwnedQueryParams(), {
            context: {
                pivot_column_groupby: [],
                pivot_measures: ['foo'],
                pivot_row_groupby: [],
            },
        }, "context should be correct");

        await testUtils.dom.click(pivot.$('tbody .o_pivot_header_cell_closed'));
        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field="product_id"]:first'));

        assert.deepEqual(pivot.getOwnedQueryParams(), {
            context: {
                pivot_column_groupby: [],
                pivot_measures: ['foo'],
                pivot_row_groupby: ['product_id'],
            },
        }, "context should be correct");

        await testUtils.dom.click(pivot.$('thead .o_pivot_header_cell_closed'));
        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field="customer"]:first'));

        assert.deepEqual(pivot.getOwnedQueryParams(), {
            context: {
                pivot_column_groupby: ['customer'],
                pivot_measures: ['foo'],
                pivot_row_groupby: ['product_id'],
            },
        }, "context should be correct");

        pivot.destroy();
    });

    QUnit.test('Unload Filter, reset display, load another filter', async function (assert) {
        assert.expect(18);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
            viewOptions: {
                context: {
                    pivot_measures: ['foo'],
                    pivot_column_groupby: ['customer'],
                    pivot_row_groupby: ['product_id'],
                },
            },
        });

        // Check Columns
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_opened').length, 1,
            'The column should be grouped');
        assert.strictEqual(pivot.$('thead tr:contains("First")').length, 1,
            'There should be a column "First"');
        assert.strictEqual(pivot.$('thead tr:contains("Second")').length, 1,
            'There should be a column "Second"');

        // Check Rows
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_opened').length, 1,
            'The row should be grouped');
        assert.strictEqual(pivot.$('tbody tr:contains("xphone")').length, 1,
            'There should be a row "xphone"');
        assert.strictEqual(pivot.$('tbody tr:contains("xpad")').length, 1,
            'There should be a row "xpad"');

        // Equivalent to unload the filter
        var reloadParams = {
            context: {},
        };
        await pivot.reload(reloadParams);
        // collapse all headers
        await testUtils.dom.click(pivot.$('.o_pivot_header_cell_opened:first'));
        await testUtils.dom.click(pivot.$('.o_pivot_header_cell_opened'));

        // Check Columns
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed').length, 1,
            'The column should not be grouped');
        assert.strictEqual(pivot.$('thead tr:contains("First")').length, 0,
            'There should not be a column "First"');
        assert.strictEqual(pivot.$('thead tr:contains("Second")').length, 0,
            'There should not be a column "Second"');

        // Check Rows
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed').length, 1,
            'The row should not be grouped');
        assert.strictEqual(pivot.$('tbody tr:contains("xphone")').length, 0,
            'There should not be a row "xphone"');
        assert.strictEqual(pivot.$('tbody tr:contains("xpad")').length, 0,
            'There should not be a row "xpad"');

        // Equivalent to load another filter
        reloadParams = {
            context: {
                pivot_measures: ['foo'],
                pivot_column_groupby: ['customer'],
                pivot_row_groupby: ['product_id'],
            },
        };
        await pivot.reload(reloadParams);

        // Check Columns
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_opened').length, 1,
            'The column should be grouped');
        assert.strictEqual(pivot.$('thead tr:contains("First")').length, 1,
            'There should be a column "First"');
        assert.strictEqual(pivot.$('thead tr:contains("Second")').length, 1,
            'There should be a column "Second"');

        // Check Rows
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_opened').length, 1,
            'The row should be grouped');
        assert.strictEqual(pivot.$('tbody tr:contains("xphone")').length, 1,
            'There should be a row "xphone"');
        assert.strictEqual(pivot.$('tbody tr:contains("xpad")').length, 1,
            'There should be a row "xpad"');

        pivot.destroy();
    });

    QUnit.test('Reload, group by columns, reload', async function (assert) {
        assert.expect(2);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot/>',
        });

        // Set a column groupby
        pivot.$('thead .o_pivot_header_cell_closed').click();
        await testUtils.dom.click(pivot.$('.o_field_selection .dropdown-item[data-field=customer]'));

        // Set a domain
        await pivot.update({domain: [['product_id', '=', 37]], groupBy: [], context: {}});

        var expectedContext = {pivot_column_groupby: ['customer'],
                               pivot_measures: ['__count'],
                               pivot_row_groupby: []};

        // Check that column groupbys were not lost
        assert.deepEqual(pivot.getOwnedQueryParams(), {context: expectedContext},
            'Column groupby not lost after first reload');

        // Set a column groupby
        pivot.$('thead .o_pivot_header_cell_closed').click();
        await testUtils.dom.click(pivot.$('.o_field_selection .dropdown-item[data-field=product_id]'));

        // Set a domain
        await pivot.update({domain: [['product_id', '=', 41]], groupBy: [], context: {}});

        expectedContext = {pivot_column_groupby: ['customer', 'product_id'],
                           pivot_measures: ['__count'],
                           pivot_row_groupby: []};

        assert.deepEqual(pivot.getOwnedQueryParams(), {context: expectedContext},
            'Column groupby not lost after second reload');

        pivot.destroy();
    });

    QUnit.test('folded groups remain folded at reload', async function (assert) {
        assert.expect(5);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="row"/>' +
                        '<field name="company_type" type="col"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        var values = [
            "29", "3", "32",
            "12",      "12",
            "17", "3", "20",
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join(','));

        // expand a col group
        await testUtils.dom.click(pivot.$('thead .o_pivot_header_cell_closed:nth(1)'));
        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field="customer"]'));

        values = [
            "29", "1", "2", "32",
            "12",           "12",
            "17", "1", "2", "20",
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join(','));

        // expand a row group
        await testUtils.dom.click(pivot.$('tbody .o_pivot_header_cell_closed:nth(1)'));
        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field="other_product_id"]'));

        values = [
            "29", "1", "2", "32",
            "12",           "12",
            "17", "1", "2", "20",
            "17", "1", "2", "20",
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join(','));

        // reload (should keep folded groups folded as col/row groupbys didn't change)
        await testUtils.pivot.reload(pivot, {context: {}, domain: [], groupBy: []});

        assert.strictEqual(getCurrentValues(pivot), values.join(','));

        await testUtils.dom.click(pivot.$('.o_pivot_expand_button'));

        // sanity check of what the table should look like if all groups are
        // expanded, to ensure that the former asserts are pertinent
        values = [
            "12", "17", "1", "2", "32",
            "12",                 "12",
            "12",                 "12",
                  "17", "1", "2", "20",
                  "17", "1", "2", "20",
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join(','));

        pivot.destroy();
    });

    QUnit.test('Empty results keep groupbys', async function (assert) {
        assert.expect(2);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot/>',
        });

        // Set a column groupby
        pivot.$('thead .o_pivot_header_cell_closed').click();
        pivot.$('.o_field_selection .dropdown-item[data-field=customer]').click();

        // Set a domain for empty results
        await pivot.update({domain: [['id', '=', false]]});

        var expectedContext = {pivot_column_groupby: ['customer'],
                               pivot_measures: ['__count'],
                               pivot_row_groupby: []};
        assert.deepEqual(pivot.getOwnedQueryParams(), {context: expectedContext},
            'Column groupby not lost after empty results');

        // Set a domain for not empty results
        await pivot.update({domain: [['product_id', '=', 37]]});

        assert.deepEqual(pivot.getOwnedQueryParams(), {context: expectedContext},
            'Column groupby not lost after reload after empty results');

        pivot.destroy();
    });

    QUnit.test('correctly uses pivot_ keys from the context', async function (assert) {
        assert.expect(7);

        this.data.partner.fields.amount = {string: "Amount", type: "float", group_operator: 'sum'};

        var pivot = await createView({
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

        assert.containsOnce(pivot, 'thead .o_pivot_header_cell_opened',
            "column: should have one opened header");
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed:contains(First)').length, 1,
            "column: should display one closed header with 'First'");
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed:contains(Second)').length, 1,
            "column: should display one closed header with 'Second'");

        assert.containsOnce(pivot, 'tbody .o_pivot_header_cell_opened',
            "row: should have one opened header");
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xphone)').length, 1,
            "row: should display one closed header with 'xphone'");
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xpad)').length, 1,
            "row: should display one closed header with 'xpad'");

        assert.strictEqual(pivot.$('tbody tr:first td:nth(2)').text(), '32',
            "selected measure should be foo, with total 32");

        pivot.destroy();
    });

    QUnit.test('clear table cells data after closeGroup', async function (assert) {
        assert.expect(2);

        const pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot/>',
            groupBy: ['product_id'],
        });

        await testUtils.dom.click(pivot.el.querySelector('thead .o_pivot_header_cell_closed'));
        await testUtils.dom.click(pivot.el.querySelectorAll('.o_pivot_field_menu .dropdown-item[data-field="date"]')[0]);

        // close and reopen row groupings after changing value
        this.data.partner.records.find(r => r.product_id === 37).date = '2016-10-27';
        await testUtils.dom.click(pivot.el.querySelector('tbody .o_pivot_header_cell_opened'));
        await testUtils.dom.click(pivot.el.querySelector('tbody .o_pivot_header_cell_closed'));
        await testUtils.dom.click(pivot.el.querySelector('.o_pivot_field_menu .dropdown-item[data-field="product_id"]'));
        assert.strictEqual(pivot.el.querySelectorAll('.o_pivot_cell_value')[4].innerText, ''); // xphone December 2016

        // invert axis, and reopen column groupings
        await testUtils.dom.click(pivot.el.querySelector('.o_cp_buttons .o_pivot_flip_button'));
        await testUtils.dom.click(pivot.el.querySelector('thead .o_pivot_header_cell_opened'));
        await testUtils.dom.click(pivot.el.querySelector('thead .o_pivot_header_cell_closed'));
        await testUtils.dom.click(pivot.el.querySelector('.o_pivot_field_menu .dropdown-item[data-field="product_id"]'));
        assert.strictEqual(pivot.el.querySelectorAll('.o_pivot_cell_value')[3].innerText, ''); // December 2016 xphone

        pivot.destroy();
    });

    QUnit.test('correctly uses pivot_ keys from the context (at reload)', async function (assert) {
        assert.expect(8);

        this.data.partner.fields.amount = {string: "Amount", type: "float", group_operator: 'sum'};

        var pivot = await createView({
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
        await testUtils.pivot.reload(pivot, reloadParams);

        assert.containsOnce(pivot, 'thead .o_pivot_header_cell_opened',
            "column: should have one opened header");
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed:contains(First)').length, 1,
            "column: should display one closed header with 'First'");
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed:contains(Second)').length, 1,
            "column: should display one closed header with 'Second'");

        assert.containsOnce(pivot, 'tbody .o_pivot_header_cell_opened',
            "row: should have one opened header");
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xphone)').length, 1,
            "row: should display one closed header with 'xphone'");
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xpad)').length, 1,
            "row: should display one closed header with 'xpad'");

        assert.strictEqual(pivot.$('tbody tr:first td:nth(2)').text(), '32',
            "selected measure should be foo, with total 32");

        pivot.destroy();
    });

    QUnit.test('correctly use group_by key from the context', async function (assert) {
        assert.expect(7);

        var pivot = await createView({
            View: PivotView,
            model: 'partner',
            data: this.data,
            arch: '<pivot>' +
                        '<field name="customer" type="col" />' +
                        '<field name="foo" type="measure" />' +
                '</pivot>',
            groupBy: ['product_id'],
        });

        assert.containsOnce(pivot, 'thead .o_pivot_header_cell_opened',
            'column: should have one opened header');
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed:contains(First)').length, 1,
            'column: should display one closed header with "First"');
        assert.strictEqual(pivot.$('thead .o_pivot_header_cell_closed:contains(Second)').length, 1,
            'column: should display one closed header with "Second"');

        assert.containsOnce(pivot, 'tbody .o_pivot_header_cell_opened',
            'row: should have one opened header');
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xphone)').length, 1,
            'row: should display one closed header with "xphone"');
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xpad)').length, 1,
            'row: should display one closed header with "xpad"');

        assert.strictEqual(pivot.$('tbody tr:first td:nth(2)').text(), '32',
            'selected measure should be foo, with total 32');

        pivot.destroy();
    });

    QUnit.test('correctly uses pivot_row_groupby key with default groupBy from the context', async function (assert) {
        assert.expect(6);

        this.data.partner.fields.amount = {string: "Amount", type: "float", group_operator: 'sum'};

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="customer" type="col"/>' +
                        '<field name="date" interval="day" type="row"/>' +
                '</pivot>',
            groupBy: ['customer'],
            viewOptions: {
                context: {
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

        // With pivot_row_groupby, groupBy customer should replace and eventually display product_id
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_opened').length, 1,
            "row: should have one opened header");
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xphone)').length, 1,
            "row: should display one closed header with 'xphone'");
        assert.strictEqual(pivot.$('tbody .o_pivot_header_cell_closed:contains(xpad)').length, 1,
            "row: should display one closed header with 'xpad'");

        pivot.destroy();
    });

    QUnit.test('pivot still handles __count__ measure', async function (assert) {
        // for retro-compatibility reasons, the pivot view still handles
        // '__count__' measure.
        assert.expect(2);

        var pivot = await createView({
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
        assert.hasClass($countMeasure,'selected', "The count measure should be activated");

        pivot.destroy();
    });

    QUnit.test('not use a many2one as a measure by default', async function (assert) {
        assert.expect(1);

        var pivot = await createView({
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

    QUnit.test('use a many2one as a measure with specified additional measure', async function (assert) {
        assert.expect(1);

        var pivot = await createView({
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

    QUnit.test('pivot view with many2one field as a measure', async function (assert) {
        assert.expect(1);

        var pivot = await createView({
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

    QUnit.test('m2o as measure, drilling down into data', async function (assert) {
        assert.expect(1);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="measure"/>' +
                '</pivot>',
        });
        await testUtils.dom.click(pivot.$('tbody .o_pivot_header_cell_closed'));
        // click on date by month
        pivot.$('.dropdown-menu.show .o_inline_dropdown .dropdown-menu').toggle(); // unfold inline dropdown
        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field="date"][data-interval="month"]'));

        assert.strictEqual(pivot.$('.o_pivot_cell_value').text(), '2211',
            'should have loaded the proper data');
        pivot.destroy();
    });

    QUnit.test('pivot view with same many2one field as a measure and grouped by', async function (assert) {
        assert.expect(1);

        var pivot = await createView({
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

        await testUtils.pivot.toggleMeasuresDropdown(pivot);
        await testUtils.pivot.clickMeasure(pivot, 'product_id');
        assert.strictEqual(pivot.$('.o_pivot_cell_value').text(), '421131',
            'should have loaded the proper data');
        pivot.destroy();
    });

    QUnit.test('pivot view with same many2one field as a measure and grouped by (and drill down)', async function (assert) {
        assert.expect(1);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="product_id" type="measure"/>' +
                '</pivot>',
        });

        await testUtils.dom.click(pivot.$('tbody .o_pivot_header_cell_closed'));

        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field="product_id"]:first'));

        assert.strictEqual(pivot.$('.o_pivot_cell_value').text(), '211',
            'should have loaded the proper data');
        pivot.destroy();
    });

    QUnit.test('Row and column groupbys plus a domain', async function (assert) {
        assert.expect(3);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
        });

        // Set a column groupby
        await testUtils.dom.click(pivot.$('thead .o_pivot_header_cell_closed'));
        await testUtils.dom.click(pivot.$('.o_field_selection .dropdown-item[data-field=customer]:first'));

        // Set a Row groupby
        await testUtils.dom.click(pivot.$('tbody .o_pivot_header_cell_closed'));
        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field=product_id]:first'));

        // Set a domain
        await testUtils.pivot.reload(pivot, {domain: [['product_id', '=', 41]]});

        var expectedContext = {
            context: {
                pivot_column_groupby: ['customer'],
                pivot_measures: ['foo'],
                pivot_row_groupby: ['product_id'],
            },
        };

        // Mock 'save as favorite'
        assert.deepEqual(pivot.getOwnedQueryParams(), expectedContext,
            'The pivot view should have the right context');

        var $xpadHeader = pivot.$('tbody .o_pivot_header_cell_closed[data-original-title=Product]');
        assert.equal($xpadHeader.length, 1,
            'There should be only one product line because of the domain');

        assert.equal($xpadHeader.text(), 'xpad',
            'The product should be the right one');

        pivot.destroy();
    });

    QUnit.test('parallel data loading should discard all but the last one', async function (assert) {
        assert.expect(2);

        var def;

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                      '<field name="foo" type="measure"/>' +
                  '</pivot>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'read_group') {
                    return Promise.resolve(def).then(_.constant(result));
                }
                return result;
            },
        });

        def = testUtils.makeTestPromise();
        testUtils.pivot.reload(pivot, {groupBy: ['product_id']});
        testUtils.pivot.reload(pivot, {groupBy: ['product_id', 'customer']});
        await def.resolve();
        await testUtils.nextTick();
        assert.containsN(pivot, '.o_pivot_cell_value', 6,
            "should have 6 cells");
        assert.containsN(pivot, 'tbody tr', 6,
            "should have 6 rows");
        pivot.destroy();
    });

    QUnit.test('pivot measures should be alphabetically sorted', async function (assert) {
        assert.expect(2);

        var data = this.data;
        // It's important to compare capitalized and lowercased words
        // to be sure the sorting is effective with both of them
        data.partner.fields.bouh = {string: "bouh", type: "integer", group_operator: 'sum'};
        data.partner.fields.modd = {string: "modd", type: "integer", group_operator: 'sum'};
        data.partner.fields.zip = {string: "Zip", type: "integer", group_operator: 'sum'};

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: data,
            arch: '<pivot>' +
                        '<field name="zip" type="measure"/>' +
                        '<field name="foo" type="measure"/>' +
                        '<field name="bouh" type="measure"/>' +
                        '<field name="modd" type="measure"/>' +
                  '</pivot>',
        });
        assert.strictEqual(pivot.$buttons.find('.o_pivot_measures_list .dropdown-item:first').data('field'), 'bouh',
            "Bouh should be the first measure");
        assert.strictEqual(pivot.$buttons.find('.o_pivot_measures_list .dropdown-item:last').data('field'), '__count',
            "Count should be the last measure");

        pivot.destroy();
    });

    QUnit.test('pivot view should use default order for auto sorting', async function (assert) {
        assert.expect(1);

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot default_order="foo asc">' +
                        '<field name="foo" type="measure"/>' +
                  '</pivot>',
        });

        assert.hasClass(pivot.$('thead tr:last th:last'), 'o_pivot_sort_order_asc',
                        "Last thead should be sorted in ascending order");

        pivot.destroy();
    });

    QUnit.test('pivot view can be flipped', async function (assert) {
        assert.expect(5);

        var rpcCount = 0;

        var pivot = await createView({
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

        assert.containsN(pivot, 'tbody tr', 3,
            "should have 3 rows: 1 for the open header, and 2 for data");
        var values = [
            "4",
            "1",
            "3"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        rpcCount = 0;
        await testUtils.dom.click(pivot.$buttons.find('.o_pivot_flip_button'));

        assert.strictEqual(rpcCount, 0, "should not have done any rpc");
        assert.containsOnce(pivot, 'tbody tr',
            "should have 1 rows: 1 for the main header");

        values = [
            "1", "3", "4"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        pivot.destroy();
    });

    QUnit.test('rendering of pivot view with comparison', async function (assert) {
        assert.expect(7);

        this.data.partner.records[0].date = '2016-12-15';
        this.data.partner.records[1].date = '2016-12-17';
        this.data.partner.records[2].date = '2016-11-22';
        this.data.partner.records[3].date = '2016-11-03';


        var unpatchDate = patchDate(2016, 11, 20, 1, 0, 0);

        var pivot = await createView({
            View: PivotView,
            model: 'partner',
            data: this.data,
            arch: '<pivot>' +
                    '<field name="date" interval="month" type="col"/>' +
                    '<field name="foo" type="measure"/>' +
              '</pivot>',
            viewOptions: {
                additionalMeasures: ['product_id'],
            },
            intercepts: {
                create_filter: function (ev) {
                    var data = ev.data;
                    assert.deepEqual(data.filter.context.timeRangeMenuData, {
                        timeRange: ["&", ["date", ">=", "2016-12-01"], ["date", "<", "2017-01-01"]],
                        timeRangeDescription: 'This Month',
                        comparisonTimeRange: ["&", ["date", ">=", "2016-11-01"], ["date", "<", "2016-12-01"]],
                        comparisonTimeRangeDescription: 'Previous Period',
                    });
                }
            },
        });

        // with no data
        await testUtils.dom.click(pivot.$('.o_time_range_menu_button'));
        await testUtils.dom.click(pivot.$('.o_time_range_menu .o_comparison_checkbox'));
        pivot.$('.o_time_range_selector').val('today');
        await testUtils.dom.click(pivot.$('.o_time_range_menu .o_apply_range'));

        assert.strictEqual(pivot.$('.o_pivot p.o_view_nocontent_empty_folder').length, 1);

        // with data, no row groupby
        await testUtils.dom.click(pivot.$('.o_time_range_menu_button'));
        pivot.$('.o_time_range_selector').val('this_month');
        await testUtils.dom.click(pivot.$('.o_time_range_menu .o_apply_range'));
        assert.containsN(pivot, '.o_pivot thead tr:last th', 9,
            "last header row should contains 9 cells (3*[This month, Previous Period, Variation]");
        var values = [
            "13", "0", "100%", "0", "19", "-100%", "13", "19", "-31.58%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        // with data, with row groupby
        await testUtils.dom.click(pivot.$('.o_pivot .o_pivot_header_cell_closed').eq(2));
        await testUtils.dom.click(pivot.$('.o_pivot .o_field_selection a[data-field="product_id"]'));
        values = [
            "13", "0", "100%", "0", "19", "-100%", "13", "19", "-31.58%",
            "12", "0", "100%",                     "12", "0" , "100%",
            "1" , "0", "100%", "0", "19", "-100%", "1" , "19", "-94.74%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        await testUtils.pivot.toggleMeasuresDropdown(pivot);
        await testUtils.dom.click(pivot.$('.o_control_panel div.o_pivot_measures_list a[data-field="foo"]'));
        await testUtils.dom.click(pivot.$('.o_control_panel div.o_pivot_measures_list a[data-field="product_id"]'));
        values = [
            "2", "0", "100%", "0", "1", "-100%", "2", "1", "100%",
            "1", "0", "100%",                    "1", "0", "100%",
            "1", "0", "100%", "0", "1", "-100%", "1", "1", "0%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        await testUtils.dom.click(pivot.$('.o_control_panel div.o_pivot_measures_list a[data-field="__count"]'));
        await testUtils.dom.click(pivot.$('.o_control_panel div.o_pivot_measures_list a[data-field="product_id"]'));
        values = [
            "2", "0", "100%", "0", "2", "-100%", "2", "2", "0%",
            "1", "0", "100%",                    "1", "0", "100%",
            "1", "0", "100%", "0", "2", "-100%", "1", "2", "-50%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        await testUtils.dom.clickFirst(pivot.$('.o_pivot .o_pivot_header_cell_opened'));
        values = [
            "2", "2", "0%",
            "1", "0", "100%",
            "1", "2", "-50%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        pivot.$('.o_search_options button:contains("Favorites")').click();
        var $favorites = pivot.$('.dropdown-menu.o_favorites_menu');
        $favorites.find('a.o_save_search').click();
        $favorites.find('.o_input').val('Fav').trigger('input');
        $favorites.find('button').click();

        unpatchDate();
        pivot.destroy();
    });

    QUnit.test('export data in excel with comparison', async function (assert) {
        assert.expect(11);

        this.data.partner.records[0].date = '2016-12-15';
        this.data.partner.records[1].date = '2016-12-17';
        this.data.partner.records[2].date = '2016-11-22';
        this.data.partner.records[3].date = '2016-11-03';

        var unpatchDate = patchDate(2016, 11, 20, 1, 0, 0);

        var pivot = await createView({
            View: PivotView,
            model: 'partner',
            data: this.data,
            arch: '<pivot>' +
                    '<field name="date" interval="month" type="col"/>' +
                    '<field name="foo" type="measure"/>' +
              '</pivot>',
            session: {
                get_file: function (args) {
                    var data = JSON.parse(args.data.data);
                    _.each(data.col_group_headers, function (l) {
                        var titles = l.map(function (o) {
                            return o.title;
                        });
                        assert.step(JSON.stringify(titles));
                    });
                    var measures = data.measure_headers.map(function (o) {
                        return o.title;
                    });
                    assert.step(JSON.stringify(measures));
                    var origins = data.origin_headers.map(function (o) {
                        return o.title;
                    });
                    assert.step(JSON.stringify(origins));
                    assert.step(String(data.measure_count));
                    assert.step(String(data.origin_count));
                    var valuesLength = data.rows.map(function (o) {
                        return o.values.length;
                    });
                    assert.step(JSON.stringify(valuesLength));
                    assert.strictEqual(args.url, '/web/pivot/export_xls',
                        "should call get_file with correct parameters");
                    args.complete();
                },
            },
        });

        // open time range menu
        await testUtils.dom.click(pivot.$('.o_control_panel .o_time_range_menu_button'));
        // select 'Today' as range
        pivot.$('.o_control_panel .o_time_range_selector').val('today');
        // check checkbox 'Compare To'
        await testUtils.dom.click(pivot.$('.o_control_panel .o_time_range_menu .o_comparison_checkbox'));
        // Click on 'Apply' button
        await testUtils.dom.click(pivot.$('.o_control_panel .o_time_range_menu .o_apply_range'));

        // the time range menu configuration is by now: Date, Today, checkbox checked, Previous Period
        // With the data above, the time ranges contain no record.
        assert.strictEqual(pivot.$('.o_pivot p.o_view_nocontent_empty_folder').length, 1, "there should be no data");
        // export data should be impossible since the pivot buttons
        // are deactivated (exception: the 'Measures' button).
        assert.ok(pivot.$('.o_control_panel button.o_pivot_download').prop('disabled'));

        // open time range menu
        await testUtils.dom.click(pivot.$('.o_control_panel .o_time_range_menu_button'));
        // select 'This Month' as date range
        pivot.$('.o_control_panel .o_time_range_selector').val('this_month');

        // Click on 'Apply' button
        await testUtils.dom.click(pivot.$('.o_control_panel .o_time_range_menu .o_apply_range'));
        // the time range menu configuration is by now: Date, This Month, checkbox checked, Previous Period
        // With the data above, the time ranges contain some records.
        // export data. Should execute 'get_file'
        await testUtils.dom.click(pivot.$('.o_control_panel button.o_pivot_download'));

        assert.verifySteps([
            // col group headers
            '["Total",""]',
            '["December 2016","November 2016"]',
            // measure headers
            '["Foo","Foo","Foo"]',
            // origin headers
            '["This Month","Previous Period","Variation","This Month","Previous Period"' +
                ',"Variation","This Month","Previous Period","Variation"]',
            // number of 'measures'
            '1',
            // number of 'origins'
            '2',
            // rows values length
            '[9]',
        ]);

        unpatchDate();
        pivot.destroy();
    });

    QUnit.test('rendering of pivot view with comparison and count measure', async function (assert) {
        assert.expect(2);

        var mockMock = false;
        var nbReadGroup = 0;

        this.data.partner.records[0].date = '2016-12-15';
        this.data.partner.records[1].date = '2016-12-17';
        this.data.partner.records[2].date = '2016-12-22';
        this.data.partner.records[3].date = '2016-12-03';

        var unpatchDate = patchDate(2016, 11, 20, 1, 0, 0);

        var pivot = await createView({
            View: PivotView,
            model: 'partner',
            data: this.data,
            arch: '<pivot><field name="customer" type="row"/></pivot>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'read_group' && mockMock) {
                    nbReadGroup++;
                    if (nbReadGroup === 4) {
                        // this modification is necessary because mockReadGroup does not
                        // properly reflect the server response when there is no record
                        // and a groupby list of length at least one.
                        return Promise.resolve([{}]);
                    }
                }
                return result;
            },
        });

        mockMock = true;

        // activate 'This Month' and 'Previous Period' in time range menu
        await testUtils.dom.click(pivot.$('.o_control_panel .o_time_range_menu_button'));
        pivot.$('.o_control_panel .o_time_range_selector').val('this_month');
        await testUtils.dom.click(pivot.$('.o_control_panel .o_time_range_menu .o_comparison_checkbox'));
        await testUtils.dom.click(pivot.$('.o_control_panel .o_time_range_menu .o_apply_range'));

        var values = [
            "4", "0", "100%",
            "2", "0", "100%",
            "2", "0", "100%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join(','));
        assert.strictEqual(pivot.$('.o_pivot_header_cell_closed').length, 3,
            "there should be exactly three closed header ('Total','First', 'Second')");

        unpatchDate();
        pivot.destroy();
    });

    QUnit.test('can sort a pivot view with comparison by clicking on header', async function (assert) {
        assert.expect(6);

        this.data.partner.records[0].date = '2016-12-15';
        this.data.partner.records[1].date = '2016-12-17';
        this.data.partner.records[2].date = '2016-11-22';
        this.data.partner.records[3].date = '2016-11-03';

        var unpatchDate = patchDate(2016, 11, 20, 1, 0, 0);
        var pivot = await createView({
            View: PivotView,
            model: 'partner',
            data: this.data,
            arch: '<pivot>' +
                    '<field name="date" interval="day" type="row"/>' +
                    '<field name="company_type" type="col"/>' +
                    '<field name="foo" type="measure"/>' +
                '</pivot>',
            viewOptions: {
                additionalMeasures: ['product_id'],
            },
        });

        // enable comparison mode
        var $cp = pivot.$('.o_control_panel');
        // open time range menu
        await testUtils.dom.click($cp.find('.o_time_range_menu_button'));
        // select 'This month' as range
        await testUtils.fields.editInput($cp.find('.o_time_range_selector'), 'this_month');
        // check checkbox 'Compare To'
        await testUtils.dom.click($cp.find('.o_time_range_menu .o_comparison_checkbox'));
        // click on 'Apply' button
        await testUtils.dom.click($cp.find('.o_time_range_menu .o_apply_range'));

        // initial sanity check
        var values = [
            "12", "17", "-29.41%", "1", "2", "-50%" , "13", "19", "-31.58%",
            "12", "0" , "100%",                       "12", "0" , "100%",
                                   "1", "0", "100%" , "1" , "0" , "100%",
            "0" , "17", "-100%",                      "0" , "17", "-100%",
                                   "0", "2", "-100%", "0" , "2" , "-100%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        // click on 'Foo' in column Total/Company (should sort by the period of interest, ASC)
        await testUtils.dom.click(pivot.$('.o_pivot_measure_row').eq(0));
        values = [
            "12", "17", "-29.41%", "1", "2", "-50%" , "13", "19", "-31.58%",
                                   "1", "0", "100%" , "1" , "0" , "100%",
            "0" , "17", "-100%",                      "0" , "17", "-100%",
                                   "0", "2", "-100%", "0" , "2" , "-100%",
            "12", "0" , "100%",                       "12", "0" , "100%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        // click again on 'Foo' in column Total/Company (should sort by the period of interest, DESC)
        await testUtils.dom.click(pivot.$('.o_pivot_measure_row').eq(0));
        values = [
            "12", "17", "-29.41%", "1", "2", "-50%" , "13", "19", "-31.58%",
            "12", "0" , "100%",                       "12", "0" , "100%",
                                   "1", "0", "100%" , "1" , "0" , "100%",
            "0" , "17", "-100%",                      "0" , "17", "-100%",
                                   "0", "2", "-100%", "0" , "2" , "-100%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        // click on 'This Month' in column Total/Individual/Foo
        await testUtils.dom.click(pivot.$('.o_pivot_origin_row').eq(3));
        values = [
            "12", "17", "-29.41%", "1", "2", "-50%",  "13", "19", "-31.58%",
            "12", "0",  "100%",                       "12", "0" , "100%",
            "0",  "17", "-100%",                      "0",  "17", "-100%",
                                   "0", "2", "-100%", "0" , "2" , "-100%",
                                   "1", "0", "100%",  "1" , "0",  "100%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        // click on 'Previous Period' in column Total/Individual/Foo
        await testUtils.dom.click(pivot.$('.o_pivot_origin_row').eq(4));
        values = [
            "12", "17", "-29.41%", "1", "2", "-50%",  "13", "19", "-31.58%",
            "12", "0",  "100%",                       "12", "0" , "100%",
                                   "1", "0", "100%",  "1" , "0",  "100%",
            "0",  "17", "-100%",                      "0",  "17", "-100%",
                                   "0", "2", "-100%", "0" , "2" , "-100%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        // click on 'Variation' in column Total/Foo
        await testUtils.dom.click(pivot.$('.o_pivot_origin_row').eq(8));
        values = [
            "12", "17", "-29.41%", "1", "2", "-50%",  "13", "19", "-31.58%",
            "0",  "17", "-100%",                      "0",  "17", "-100%",
                                   "0", "2", "-100%", "0" , "2" , "-100%",
            "12", "0",  "100%",                       "12", "0" , "100%",
                                   "1", "0", "100%",  "1" , "0",  "100%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        unpatchDate();
        pivot.destroy();
    });

    QUnit.test('Click on the measure list but not on a menu item', async function (assert) {
        assert.expect(2);

        const pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: `<pivot/>`,
        });

        // open the "Measures" menu
        await testUtils.dom.click(pivot.el.querySelector('.o_cp_buttons button'));

        // click on the divider in the "Measures" menu does not crash
        await testUtils.dom.click(pivot.el.querySelector('.o_pivot_measures_list .dropdown-divider'));
        // the menu should still be open
        assert.isVisible(pivot.el.querySelector('.o_pivot_measures_list'));

        // click on the measure list but not on a menu item or the separator
        await testUtils.dom.click(pivot.el.querySelector('.o_pivot_measures_list'));
        // the menu should still be open
        assert.isVisible(pivot.el.querySelector('.o_pivot_measures_list'));

        pivot.destroy();
    });

    QUnit.test('Navigation list view for a group and back with breadcrumbs', async function (assert) {
        assert.expect(16);
        // create an action manager to test the interactions with the search view
        var readGroupCount = 0;
        var actionManager = await createActionManager({
            data: this.data,
            archs: {
                'partner,false,pivot': '<pivot>' +
                        '<field name="customer" type="row"/>' +
                  '</pivot>',
                'partner,false,search': '<search><filter name="bayou" string="Bayou" domain="[(\'foo\',\'=\', 12)]"/></search>',
                'partner,false,list': '<tree><field name="foo"/></tree>',
                'partner,false,form': '<form><field name="foo"/></form>',
            },
            intercepts: {
                do_action: function (event) {
                    var action = event.data.action;
                    actionManager.doAction(action);
                }
            },
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.step('read_group');
                    var domain = args.kwargs.domain;
                    if ([0,1].indexOf(readGroupCount) !== -1) {
                        assert.deepEqual(domain, [], 'initial domain empty');
                    } else if ([2,3,4,5].indexOf(readGroupCount) !== -1) {
                        assert.deepEqual(domain, [['foo', '=', 12]],
                            'domain conserved when back with breadcrumbs');
                    }
                    readGroupCount++;
                }
                if (route === '/web/dataset/search_read') {
                    assert.step('search_read');
                    var domain = args.domain;
                    assert.deepEqual(domain, [['customer', '=', 1], ['foo', '=', 12]],
                        'list domain is correct');
                }
                return this._super.apply(this, arguments);
            }
        });

        await actionManager.doAction({
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'pivot']],
        });

        await testUtilsDom.click(actionManager.$('.o_filters_menu_button'));
        await testUtilsDom.click(actionManager.$('.o_menu_item:contains("Bayou")'));

        await testUtilsDom.click(actionManager.$('.o_pivot_cell_value:nth(1)'))

        assert.containsOnce(actionManager, '.o_list_view');

        await testUtilsDom.click(actionManager.$('.o_control_panel .breadcrumb-item:first() a'));

        assert.verifySteps([
            'read_group', 'read_group',
            'read_group', 'read_group',
            'search_read',
            'read_group', 'read_group'])
        actionManager.destroy();
    });

    QUnit.test('Cell values are kept when flippin a pivot view in comparison mode', async function (assert) {
        assert.expect(2);

        this.data.partner.records[0].date = '2016-12-15';
        this.data.partner.records[1].date = '2016-12-17';
        this.data.partner.records[2].date = '2016-11-22';
        this.data.partner.records[3].date = '2016-11-03';

        var unpatchDate = patchDate(2016, 11, 20, 1, 0, 0);
        var pivot = await createView({
            View: PivotView,
            model: 'partner',
            data: this.data,
            arch: '<pivot>' +
                    '<field name="date" interval="day" type="row"/>' +
                    '<field name="company_type" type="col"/>' +
                    '<field name="foo" type="measure"/>' +
                '</pivot>',
            viewOptions: {
                additionalMeasures: ['product_id'],
            },
        });

        // enable comparison mode
        var $cp = pivot.$('.o_control_panel');
        // open time range menu
        await testUtils.dom.click($cp.find('.o_time_range_menu_button'));
        // select 'This month' as range
        await testUtils.fields.editInput($cp.find('.o_time_range_selector'), 'this_month');
        // check checkbox 'Compare To'
        await testUtils.dom.click($cp.find('.o_time_range_menu .o_comparison_checkbox'));
        // click on 'Apply' button
        await testUtils.dom.click($cp.find('.o_time_range_menu .o_apply_range'));

        // initial sanity check
        var values = [
            "12", "17", "-29.41%", "1", "2", "-50%" , "13", "19", "-31.58%",
            "12", "0" , "100%",                       "12", "0" , "100%",
                                   "1", "0", "100%" , "1" , "0" , "100%",
            "0" , "17", "-100%",                      "0" , "17", "-100%",
                                   "0", "2", "-100%", "0" , "2" , "-100%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        // flip table
        await testUtils.dom.click(pivot.$buttons.find('.o_pivot_flip_button'));

        values = [
            "12", "0",  "100%", "1",  "0",  "100%", "0",  "17", "-100%", "0",  "2",  "-100%", "13", "19", "-31.58%",
            "12", "0",  "100%",                     "0",  "17", "-100%",                      "12", "17", "-29.41%",
                                "1",  "0",  "100%" ,                      "0",  "2",  "-100%", "1",  "2",  "-50%"
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        unpatchDate();
        pivot.destroy();
    });

    QUnit.test('Flip then compare, table col groupbys are kept', async function (assert) {
        assert.expect(6);

        this.data.partner.records[0].date = '2016-12-15';
        this.data.partner.records[1].date = '2016-12-17';
        this.data.partner.records[2].date = '2016-11-22';
        this.data.partner.records[3].date = '2016-11-03';

        var unpatchDate = patchDate(2016, 11, 20, 1, 0, 0);
        var pivot = await createView({
            View: PivotView,
            model: 'partner',
            data: this.data,
            arch: '<pivot>' +
                    '<field name="date" interval="day" type="row"/>' +
                    '<field name="company_type" type="col"/>' +
                    '<field name="foo" type="measure"/>' +
                '</pivot>',
            viewOptions: {
                additionalMeasures: ['product_id'],
            },
        });


        assert.strictEqual(
            pivot.$('th').slice(0, 5).text(),
            [
                '', 'Total',                 '',
                    'Company', 'individual',
            ].join(''),
            "The col headers should be as expected"
        );
        assert.strictEqual(
            pivot.$('th').slice(8).text(),
            [
                'Total',
                    '2016-12-15',
                    '2016-12-17',
                    '2016-11-22',
                    '2016-11-03'
            ].join(''),
            "The row headers should be as expected"
        );

        // flip
        await testUtils.dom.click(pivot.$buttons.find('.o_pivot_flip_button'));

        assert.strictEqual(
            pivot.$('th').slice(0, 7).text(),
            [
                '', 'Total',                                                '',
                    '2016-12-15', '2016-12-17', '2016-11-22', '2016-11-03',
            ].join('')
            ,
            "The col headers should be as expected"
        );
        assert.strictEqual(
            pivot.$('th').slice(12).text(),
            [
                'Total',
                    'Company',
                    'individual'

            ].join(''),
            "The row headers should be as expected"
        );

        // enable comparison mode
        var $cp = pivot.$('.o_control_panel');
        // open time range menu
        await testUtils.dom.click($cp.find('.o_time_range_menu_button'));
        // select 'This month' as range
        await testUtils.fields.editInput($cp.find('.o_time_range_selector'), 'this_month');
        // check checkbox 'Compare To'
        await testUtils.dom.click($cp.find('.o_time_range_menu .o_comparison_checkbox'));
        // click on 'Apply' button
        await testUtils.dom.click($cp.find('.o_time_range_menu .o_apply_range'));

        assert.strictEqual(
            pivot.$('th').slice(0, 7).text(),
            [
                '', 'Total',                                                '',
                    '2016-12-15', '2016-12-17', '2016-11-22', '2016-11-03',
            ].join('')
            ,
            "The col headers should be as expected"
        );
        assert.strictEqual(
            pivot.$('th').slice(27).text(),
            [
                'Total',
                    'Company',
                    'individual'

            ].join(''),
            "The row headers should be as expected"
        );
        unpatchDate();
        pivot.destroy();
    });

    QUnit.test('correctly compute group domain when a date field has false value', async function (assert) {
        assert.expect(1);

        this.data.partner.records.forEach(r => r.date = false);

        var unpatchDate = patchDate(2016, 11, 20, 1, 0, 0);
        var pivot = await createView({
            View: PivotView,
            model: 'partner',
            data: this.data,
            arch: '<pivot o_enable_linking="1">' +
                    '<field name="date" interval="day" type="row"/>' +
                '</pivot>',
            intercepts: {
                do_action: function (ev) {
                    assert.deepEqual(ev.data.action.domain, [['date', '=', false]]);
                },
            },
        });

        await testUtils.dom.click($('td').eq(1));

        unpatchDate();
        pivot.destroy();
    });
    QUnit.test('Does not identify "false" with false as keys when creating group trees', async function (assert) {
        assert.expect(2);

        this.data.partner.fields['favorite_animal'] = {string: "Favorite animal", type: "char", store: true}
        this.data.partner.records[0]['favorite_animal'] = 'Dog'
        this.data.partner.records[1]['favorite_animal'] = 'false'
        this.data.partner.records[2]['favorite_animal'] = 'Undefined'

        var unpatchDate = patchDate(2016, 11, 20, 1, 0, 0);
        var pivot = await createView({
            View: PivotView,
            model: 'partner',
            data: this.data,
            arch: '<pivot o_enable_linking="1">' +
                    '<field name="favorite_animal" type="row"/>' +
                '</pivot>',

        });

        assert.strictEqual(
            pivot.$('th').slice(0, 2).text(),
            [
                '', 'Total',                                                '',
            ].join('')
            ,
            "The col headers should be as expected"
        );
        assert.strictEqual(
            pivot.$('th').slice(3).text(),
            [
                'Total',
                    'Dog',
                    'false',
                    'Undefined',
                    'Undefined'

            ].join(''),
            "The row headers should be as expected"
        );

        unpatchDate();
        pivot.destroy();
    });

    QUnit.test('group bys added via control panel and expand Header do not stack', async function (assert) {
        assert.expect(8);

        delete this.data.partner.fields['date']

        var pivot = await createView({
            View: PivotView,
            model: 'partner',
            data: this.data,
            arch: '<pivot>' +
                    '<field name="foo" type="measure"/>' +
                '</pivot>',
            viewOptions: {
                additionalMeasures: ['product_id'],
            },
        });

        assert.strictEqual(
            pivot.$('th').slice(0, 2).text(),
            [
                '', 'Total',
            ].join(''),
            "The col headers should be as expected"
        );
        assert.strictEqual(
            pivot.$('th').slice(3).text(),
            [
                'Total',
            ].join(''),
            "The row headers should be as expected"
        );

        var $cp = pivot.$('.o_control_panel');
        // open group by menu and add new groupby
        await testUtils.dom.click($cp.find('button span.fa-bars'));
        await testUtils.dom.click($cp.find('button.o_add_custom_group'));
        await testUtils.dom.click($cp.find('button.o_apply_group'));

        assert.strictEqual(
            pivot.$('th').slice(0, 2).text(),
            [
                '', 'Total',
            ].join(''),
            "The col headers should be as expected"
        );
        assert.strictEqual(
            pivot.$('th').slice(3).text(),
            [
                'Total',
                    'Company',
                    'individual'
            ].join(''),
            "The row headers should be as expected"
        );

        // Set a Row groupby
        await testUtils.dom.click(pivot.$('tbody .o_pivot_header_cell_closed').eq(0));
        await testUtils.dom.click(pivot.$('.o_pivot_field_menu .dropdown-item[data-field=product_id]:first'));

        assert.strictEqual(
            pivot.$('th').slice(0, 2).text(),
            [
                '', 'Total',
            ].join(''),
            "The col headers should be as expected"
        );
        assert.strictEqual(
            pivot.$('th').slice(3).text(),
            [
                'Total',
                    'Company',
                        'xphone',
                        'xpad',
                    'individual'
            ].join(''),
            "The row headers should be as expected"
        );

        // open group by menu and add new groupby
        await testUtils.dom.click($cp.find('button span.fa-bars'));
        await testUtils.dom.click($cp.find('button.o_add_custom_group'));
        await testUtils.dom.click($cp.find('button.o_apply_group'));

        assert.strictEqual(
            pivot.$('th').slice(0, 2).text(),
            [
                '', 'Total',
            ].join(''),
            "The col headers should be as expected"
        );
        assert.strictEqual(
            pivot.$('th').slice(3).text(),
            [
                'Total',
                    'Company',
                        'true',
                    'individual',
                        'true',
                        'Undefined'
            ].join(''),
            "The row headers should be as expected"
        );

        pivot.destroy();
    });

    QUnit.test('Server order is kept by default', async function (assert) {
        assert.expect(1);

        let isSecondReadGroup = false;

        var pivot = await createView({
            View: PivotView,
            model: "partner",
            data: this.data,
            arch: '<pivot>' +
                        '<field name="customer" type="row"/>' +
                        '<field name="foo" type="measure"/>' +
                '</pivot>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group' && isSecondReadGroup) {
                    return Promise.resolve([
                        {
                            customer: [2, 'Second'],
                            foo: 18,
                            __count: 2,
                            __domain :[["customer", "=", 2]],
                        },
                        {
                            customer: [1, 'First'],
                            foo: 14,
                            __count: 2,
                            __domain :[["customer", "=", 1]],
                        }
                    ]);
                }
                var result = this._super.apply(this, arguments);
                isSecondReadGroup = true;
                return result;
            },
        });

        const values = [
            "32", // Total Value
            "18", // Second
            "14", // First
        ];
        assert.strictEqual(getCurrentValues(pivot), values.join());

        pivot.destroy();
    });
});
});
