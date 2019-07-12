odoo.define('web.list_tests', function (require) {
"use strict";

var AbstractStorageService = require('web.AbstractStorageService');
var BasicModel = require('web.BasicModel');
var core = require('web.core');
var basicFields = require('web.basic_fields');
var FormView = require('web.FormView');
var ListView = require('web.ListView');
var mixins = require('web.mixins');
var NotificationService = require('web.NotificationService');
var RamStorage = require('web.RamStorage');
var testUtils = require('web.test_utils');
var widgetRegistry = require('web.widget_registry');
var Widget = require('web.Widget');

var _t = core._t;
var createActionManager = testUtils.createActionManager;
var createView = testUtils.createView;


QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "boolean"},
                    date: {string: "Some Date", type: "date"},
                    int_field: {string: "int_field", type: "integer", sortable: true, group_operator: "sum"},
                    text: {string: "text field", type: "text"},
                    qux: {string: "my float", type: "float"},
                    m2o: {string: "M2O field", type: "many2one", relation: "bar"},
                    o2m: {string: "O2M field", type: "one2many", relation: "bar"},
                    m2m: {string: "M2M field", type: "many2many", relation: "bar"},
                    amount: {string: "Monetary field", type: "monetary"},
                    currency_id: {string: "Currency", type: "many2one",
                                  relation: "res_currency", default: 1},
                    datetime: {string: "Datetime Field", type: 'datetime'},
                    reference: {string: "Reference Field", type: 'reference', selection: [
                        ["bar", "Bar"], ["res_currency", "Currency"], ["event", "Event"]]},
                },
                records: [
                    {
                        id: 1,
                        bar: true,
                        foo: "yop",
                        int_field: 10,
                        qux: 0.4,
                        m2o: 1,
                        m2m: [1, 2],
                        amount: 1200,
                        currency_id: 2,
                        date: "2017-01-25",
                        datetime: "2016-12-12 10:55:05",
                        reference: 'bar,1',
                    },
                    {id: 2, bar: true, foo: "blip", int_field: 9, qux: 13,
                     m2o: 2, m2m: [1, 2, 3], amount: 500, reference: 'res_currency,1'},
                    {id: 3, bar: true, foo: "gnap", int_field: 17, qux: -3,
                     m2o: 1, m2m: [], amount: 300, reference: 'res_currency,2'},
                    {id: 4, bar: false, foo: "blip", int_field: -4, qux: 9,
                     m2o: 1, m2m: [1], amount: 0},
                ]
            },
            bar: {
                fields: {},
                records: [
                    {id: 1, display_name: "Value 1"},
                    {id: 2, display_name: "Value 2"},
                    {id: 3, display_name: "Value 3"},
                ]
            },
            res_currency: {
                fields: {
                    symbol: {string: "Symbol", type: "char"},
                    position: {
                        string: "Position",
                        type: "selection",
                        selection: [['after', 'A'], ['before', 'B']],
                    },
                },
                records: [
                    {id: 1, display_name: "USD", symbol: '$', position: 'before'},
                    {id: 2, display_name: "EUR", symbol: '€', position: 'after'},
                ],
            },
            event: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    name: {string: "name", type: "char"},
                },
                records: [
                    {id: "2-20170808020000", name: "virtual"},
                ]
            },
        };
    }
}, function () {

    QUnit.module('ListView');

    QUnit.test('simple readonly list', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="int_field"/></tree>',
        });

        assert.doesNotHaveClass(list.$el, 'o_cannot_create',
            "should not have className 'o_cannot_create'");

        // 3 th (1 for checkbox, 2 for columns)
        assert.containsN(list, 'th', 3, "should have 3 columns");

        assert.strictEqual(list.$('td:contains(gnap)').length, 1, "should contain gnap");
        assert.containsN(list, 'tbody tr', 4, "should have 4 rows");
        assert.containsOnce(list, 'th.o_column_sortable', "should have 1 sortable column");

        assert.strictEqual(list.$('thead th:nth(2)').css('text-align'), 'right',
            "header cells of integer fields should be right aligned");
        assert.strictEqual(list.$('tbody tr:first td:nth(2)').css('text-align'), 'right',
            "integer cells should be right aligned");

        assert.isVisible(list.$buttons.find('.o_list_button_add'));
        assert.isNotVisible(list.$buttons.find('.o_list_button_save'));
        assert.isNotVisible(list.$buttons.find('.o_list_button_discard'));
        list.destroy();
    });

    QUnit.test('list with create="0"', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree create="0"><field name="foo"/></tree>',
        });

        assert.hasClass(list.$el,'o_cannot_create',
            "should have className 'o_cannot_create'");
        assert.containsNone(list.$buttons, '.o_list_button_add',
            "should not have the 'Create' button");

        list.destroy();
    });

    QUnit.test('list with delete="0"', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {hasSidebar: true},
            arch: '<tree delete="0"><field name="foo"/></tree>',
        });

        assert.isNotVisible(list.sidebar.$el, 'sidebar should be invisible');
        assert.ok(list.$('tbody td.o_list_record_selector').length, 'should have at least one record');

        await testUtils.dom.click(list.$('tbody td.o_list_record_selector:first input'));
        assert.isVisible(list.sidebar.$el, 'sidebar should be visible');
        assert.notOk(list.sidebar.$('a:contains(Delete)').length, 'sidebar should not have Delete button');

        list.destroy();
    });

    QUnit.test('editable list with edit="0"', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {hasSidebar: true},
            arch: '<tree editable="top" edit="0"><field name="foo"/></tree>',
        });

        assert.ok(list.$('tbody td.o_list_record_selector').length, 'should have at least one record');

        await testUtils.dom.click(list.$('tr td:not(.o_list_record_selector)').first());
        assert.containsNone(list, 'tbody tr.o_selected_row', "should not have editable row");

        list.destroy();
    });

    QUnit.test('simple editable rendering', async function (assert) {
        assert.expect(12);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(list, 'th', 3, "should have 2 th");
        assert.containsN(list, 'th', 3, "should have 3 th");
        assert.containsOnce(list, 'td:contains(yop)', "should contain yop");

        assert.isVisible(list.$buttons.find('.o_list_button_add'),
            "should have a visible Create button");
        assert.isNotVisible(list.$buttons.find('.o_list_button_save'),
            "should not have a visible save button");
        assert.isNotVisible(list.$buttons.find('.o_list_button_discard'),
            "should not have a visible discard button");

        await testUtils.dom.click(list.$('td:not(.o_list_record_selector)').first());

        assert.isNotVisible(list.$buttons.find('.o_list_button_add'),
            "should not have a visible Create button");
        assert.isVisible(list.$buttons.find('.o_list_button_save'),
            "should have a visible save button");
        assert.isVisible(list.$buttons.find('.o_list_button_discard'),
            "should have a visible discard button");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        assert.isVisible(list.$buttons.find('.o_list_button_add'),
            "should have a visible Create button");
        assert.isNotVisible(list.$buttons.find('.o_list_button_save'),
            "should not have a visible save button");
        assert.isNotVisible(list.$buttons.find('.o_list_button_discard'),
            "should not have a visible discard button");
        list.destroy();
    });

    QUnit.test('editable rendering with handle', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="currency_id"/>' +
                    '<field name="m2o"/>' +
                '</tree>',
        });
        assert.containsN(list, 'thead th', 4, "there should be 4 th");
        assert.hasClass(list.$('thead th:eq(0)'), 'o_list_record_selector');
        assert.hasClass(list.$('thead th:eq(1)'), 'o_handle_cell');
        assert.strictEqual(list.$('thead th:eq(1)').text(), '',
            "the handle field shouldn't have a header description");
        assert.strictEqual(list.$('thead th:eq(2)').attr('style'), "width: 50%;");
        assert.strictEqual(list.$('thead th:eq(3)').attr('style'), "width: 50%;");
        list.destroy();
    });

    QUnit.test('invisible columns are not displayed', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="bar" invisible="1"/>' +
                '</tree>',
        });

        // 1 th for checkbox, 1 for 1 visible column
        assert.containsN(list, 'th', 2, "should have 2 th");
        list.destroy();
    });

    QUnit.test('record-depending invisible lines are correctly aligned', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="bar" attrs="{\'invisible\': [(\'id\',\'=\', 1)]}"/>' +
                    '<field name="int_field"/>' +
                '</tree>',
        });

        assert.containsN(list, 'tbody tr:first td', 4,
            "there should be 4 cells in the first row");
        assert.containsOnce(list, 'tbody td.o_invisible_modifier',
            "there should be 1 invisible bar cell");
        assert.hasClass(list.$('tbody tr:first td:eq(2)'),'o_invisible_modifier',
            "the 3rd cell should be invisible");
        assert.containsN(list, 'tbody tr:eq(0) td:visible', list.$('tbody tr:eq(1) td:visible').length,
            "there should be the same number of visible cells in different rows");
        list.destroy();
    });

    QUnit.test('do not perform extra RPC to read invisible many2one fields', async function (assert) {
        assert.expect(3);

        this.data.foo.fields.m2o.default = 2;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="foo"/>' +
                    '<field name="m2o" invisible="1"/>' +
                '</tree>',
            mockRPC: function (route) {
                assert.step(_.last(route.split('/')));
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        assert.verifySteps(['search_read', 'default_get'], "no nameget should be done");

        list.destroy();
    });

    QUnit.test('editable list datetimepicker destroy widget (edition)', async function (assert) {
        assert.expect(7);
        var eventPromise = testUtils.makeTestPromise();

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="date"/>' +
                '</tree>',
        });
        list.$el.on({
            'show.datetimepicker': async function () {
                assert.containsOnce(list, '.o_selected_row');
                assert.containsOnce($('body'), '.bootstrap-datetimepicker-widget');

                await testUtils.fields.triggerKeydown(list.$('.o_datepicker_input'), 'escape');

                assert.containsOnce(list, '.o_selected_row');
                assert.containsNone($('body'), '.bootstrap-datetimepicker-widget');

                await testUtils.fields.triggerKeydown($(document.activeElement), 'escape');

                assert.containsNone(list, '.o_selected_row');

                eventPromise.resolve();
            }
        });

        assert.containsN(list, '.o_data_row', 4);
        assert.containsNone(list, '.o_selected_row');

        await testUtils.dom.click(list.$('.o_data_cell:first'));
        await testUtils.dom.openDatepicker(list.$('.o_datepicker'));

        await eventPromise;
        list.destroy();
    });

    QUnit.test('editable list datetimepicker destroy widget (new line)', async function (assert) {
        assert.expect(10);
        var eventPromise = testUtils.makeTestPromise();

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="date"/>' +
                '</tree>',
        });
        list.$el.on({
            'show.datetimepicker': async function () {
                assert.containsOnce($('body'), '.bootstrap-datetimepicker-widget');
                assert.containsN(list, '.o_data_row', 5);
                assert.containsOnce(list, '.o_selected_row');

                await testUtils.fields.triggerKeydown(list.$('.o_datepicker_input'), 'escape');

                assert.containsNone($('body'), '.bootstrap-datetimepicker-widget');
                assert.containsN(list, '.o_data_row', 5);
                assert.containsOnce(list, '.o_selected_row');

                await testUtils.fields.triggerKeydown($(document.activeElement), 'escape');

                assert.containsN(list, '.o_data_row', 4);
                assert.containsNone(list, '.o_selected_row');

                eventPromise.resolve();
            }
        });
        assert.equal(list.$('.o_data_row').length, 4,
            'There should be 4 rows');

        assert.equal(list.$('.o_selected_row').length, 0,
            'No row should be in edit mode');

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        await testUtils.dom.openDatepicker(list.$('.o_datepicker'));

        await eventPromise;
        list.destroy();
    });

    QUnit.test('at least 4 rows are rendered, even if less data', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="bar"/></tree>',
            domain: [['bar', '=', true]],
        });

        assert.containsN(list, 'tbody tr', 4, "should have 4 rows");
        list.destroy();
    });

    QUnit.test('discard a new record in editable="top" list with less than 4 records', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="bar"/></tree>',
            domain: [['bar', '=', true]],
        });

        assert.containsN(list, '.o_data_row', 3);
        assert.containsN(list, 'tbody tr', 4);

        await testUtils.dom.click(list.$('.o_list_button_add'));

        assert.containsN(list, '.o_data_row', 4);
        assert.hasClass(list.$('tbody tr:first'), 'o_selected_row');

        await testUtils.dom.click(list.$('.o_list_button_discard'));

        assert.containsN(list, '.o_data_row', 3);
        assert.containsN(list, 'tbody tr', 4);
        assert.hasClass(list.$('tbody tr:first'), 'o_data_row');

        list.destroy();
    });

    QUnit.test('basic grouped list rendering', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
        });

        assert.strictEqual(list.$('th:contains(Foo)').length, 1, "should contain Foo");
        assert.strictEqual(list.$('th:contains(Bar)').length, 1, "should contain Bar");
        assert.containsN(list, 'tr.o_group_header', 2, "should have 2 .o_group_header");
        assert.containsN(list, 'th.o_group_name', 2, "should have 2 .o_group_name");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering with widget="handle" col', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                '</tree>',
            groupBy: ['bar'],
        });

        assert.strictEqual(list.$('th:contains(Foo)').length, 1, "should contain Foo");
        assert.strictEqual(list.$('th:contains(Bar)').length, 1, "should contain Bar");
        assert.containsN(list, 'tr.o_group_header', 2, "should have 2 .o_group_header");
        assert.containsN(list, 'th.o_group_name', 2, "should have 2 .o_group_name");
        assert.containsNone(list, 'th:contains(int_field)', "Should not have int_field in grouped list");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 1 col without selector', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/></tree>',
            groupBy: ['bar'],
            hasSelectors: false,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 1,
            "group header should have exactly 1 column");
        assert.strictEqual(list.$('.o_group_header:first th').attr('colspan'), "1",
            "the header should span the whole table");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 1 col with selector', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/></tree>',
            groupBy: ['bar'],
            hasSelectors: true,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 1,
            "group header should have exactly 1 column");
        assert.strictEqual(list.$('.o_group_header:first th').attr('colspan'), "2",
            "the header should span the whole table");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 2 cols without selector', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
            hasSelectors: false,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 1,
            "group header should have exactly 1 column");
        assert.strictEqual(list.$('.o_group_header:first th').attr('colspan'), "2",
            "the header should span the whole table");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 2 col with selector', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
            hasSelectors: true,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 1,
            "group header should have exactly 1 column");
        assert.strictEqual(list.$('.o_group_header:first th').attr('colspan'), "3",
            "the header should span the whole table");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 7 cols with aggregates and selector', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="datetime"/>' +
                    '<field name="foo"/>' +
                    '<field name="int_field" sum="Sum1"/>' +
                    '<field name="bar"/>' +
                    '<field name="qux" sum="Sum2"/>' +
                    '<field name="date"/>' +
                    '<field name="text"/>' +
                '</tree>',
            groupBy: ['bar'],
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 5,
            "group header should have exactly 5 columns (one before first aggregate, one after last aggregate, and all in between");
        assert.strictEqual(list.$('.o_group_header:first th').attr('colspan'), "3",
            "header name should span on the two first fields + selector (colspan 3)");
        assert.containsN(list, '.o_group_header:first td', 3,
            "there should be 3 tds (aggregates + fields in between)");
        assert.strictEqual(list.$('.o_group_header:first th:last').attr('colspan'), "2",
            "header last cell should span on the two last fields (to give space for the pager) (colspan 2)");
        list.destroy();
    });

    QUnit.test('ordered list, sort attribute in context', async function (assert) {
        assert.expect(1);
        // Equivalent to saving a custom filter

        this.data.foo.fields.foo.sortable = true;
        this.data.foo.fields.date.sortable = true;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="date"/>' +
                '</tree>',
        });

        // Descending order on Foo
        await testUtils.dom.click(list.$('th.o_column_sortable:contains("Foo")'));
        await testUtils.dom.click(list.$('th.o_column_sortable:contains("Foo")'));

        // Ascending order on Date
        await testUtils.dom.click(list.$('th.o_column_sortable:contains("Date")'));

        var listContext = list.getOwnedQueryParams();
        assert.deepEqual(listContext,
            {
                orderedBy: [{
                    name: 'date',
                    asc: true,
                }, {
                    name: 'foo',
                    asc: false,
                }]
            }, 'the list should have the right orderedBy in context');
        list.destroy();
    });

    QUnit.test('Loading a filter with a sort attribute', async function (assert) {
        assert.expect(2);

        this.data.foo.fields.foo.sortable = true;
        this.data.foo.fields.date.sortable = true;

        var searchReads = 0;
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="date"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    if (searchReads === 0) {
                        assert.strictEqual(args.sort, 'date ASC, foo DESC',
                            'The sort attribute of the filter should be used by the initial search_read');
                    } else if (searchReads === 1) {
                        assert.strictEqual(args.sort, 'date DESC, foo ASC',
                            'The sort attribute of the filter should be used by the next search_read');
                    }
                    searchReads += 1;
                }
                return this._super.apply(this,arguments);
            },
            intercepts: {
                load_filters: function (event) {
                    return Promise.resolve([
                        {
                            context: "{}",
                            domain: "[]",
                            id: 7,
                            is_default: true,
                            name: "My favorite",
                            sort: "[\"date asc\", \"foo desc\"]",
                            user_id: [2, "Mitchell Admin"],
                        }, {
                            context: "{}",
                            domain: "[]",
                            id: 8,
                            is_default: false,
                            name: "My second favorite",
                            sort: "[\"date desc\", \"foo asc\"]",
                            user_id: [2, "Mitchell Admin"],
                        }
                    ]).then(event.data.on_success);
                },
            },
        });

        await testUtils.dom.click(list.$('.o_control_panel .o_search_options button.o_favorites_menu_button'));
        await testUtils.dom.click(list.$('.o_control_panel .o_search_options .o_favorites_menu .o_menu_item').eq(1));
        list.destroy();
    });

    QUnit.test('many2one field rendering', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="m2o"/></tree>',
        });

        assert.ok(list.$('td:contains(Value 1)').length,
            "should have the display_name of the many2one");
        list.destroy();
    });

    QUnit.test('grouped list view, with 1 open group', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="int_field"/></tree>',
            groupBy: ['foo'],
        });

        await testUtils.dom.click(list.$('th.o_group_name:nth(1)'));
        await testUtils.nextTick();
        assert.containsN(list, 'tbody:eq(1) tr', 2, "open group should contain 2 records");
        assert.containsN(list, 'tbody', 3, "should contain 3 tbody");
        assert.containsOnce(list, 'td:contains(9)', "should contain 9");
        assert.containsOnce(list, 'td:contains(-4)', "should contain -4");
        assert.containsOnce(list, 'td:contains(10)', "should contain 10");
        assert.containsOnce(list, 'tr.o_group_header td:contains(10)', "but 10 should be in a header");
        list.destroy();
    });

    QUnit.test('opening records when clicking on record', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
        });

        testUtils.mock.intercept(list, "open_record", function () {
            assert.ok("list view should trigger 'open_record' event");
        });

        testUtils.dom.click(list.$('tr td:not(.o_list_record_selector)').first());
        list.update({groupBy: ['foo']});
        await testUtils.nextTick();
        assert.containsN(list, 'tr.o_group_header', 3, "list should be grouped");
        await testUtils.dom.click(list.$('th.o_group_name').first());

        testUtils.dom.click(list.$('tr:not(.o_group_header) td:not(.o_list_record_selector)').first());
        list.destroy();
    });

    QUnit.test('editable list view: readonly fields cannot be edited', async function (assert) {
        assert.expect(4);

        this.data.foo.fields.foo.readonly = true;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                    '<field name="int_field" readonly="1"/>' +
                '</tree>',
        });
        var $td = list.$('td:not(.o_list_record_selector)').first();
        var $second_td = list.$('td:not(.o_list_record_selector)').eq(1);
        var $third_td = list.$('td:not(.o_list_record_selector)').eq(2);
        await testUtils.dom.click($td);
        assert.hasClass($td.parent(),'o_selected_row',
            "row should be in edit mode");
        assert.hasClass($td,'o_readonly_modifier',
            "foo cell should be readonly in edit mode");
        assert.doesNotHaveClass($second_td, 'o_readonly_modifier',
            "bar cell should be editable");
        assert.hasClass($third_td,'o_readonly_modifier',
            "int_field cell should be readonly in edit mode");
        list.destroy();
    });

    QUnit.test('editable list view: line with no active element', async function (assert) {
        assert.expect(3);

        this.data.bar = {
            fields: {
                titi: {string: "Char", type: "char"},
                grosminet: {string: "Bool", type: "boolean"},
            },
            records: [
                {id: 1, titi: 'cui', grosminet: true},
                {id: 2, titi: 'cuicui', grosminet: false},
            ],
        };
        this.data.foo.records[0].o2m = [1, 2];

        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            res_id: 1,
            viewOptions: { mode: 'edit' },
            arch: '<form>'+
                    '<field name="o2m">'+
                        '<tree editable="top">'+
                            '<field name="titi" readonly="1"/>'+
                            '<field name="grosminet" widget="boolean_toggle"/>'+
                        '</tree>'+
                    '</field>'+
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[1], {
                        o2m: [[1, 1, {grosminet: false}], [4, 2, false]],
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        var $td = form.$('.o_data_cell').first();
        var $td2 = form.$('.o_data_cell').eq(1);
        assert.hasClass($td, 'o_readonly_modifier');
        assert.hasClass($td2, 'o_boolean_toggle_cell');
        await testUtils.dom.click($td);
        await testUtils.dom.click($td2.find('.o_boolean_toggle input'));
        await testUtils.nextTick();

        await testUtils.form.clickSave(form);
        await testUtils.nextTick();
        form.destroy();
    });

    QUnit.test('basic operations for editable list renderer', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        var $td = list.$('td:not(.o_list_record_selector)').first();
        assert.doesNotHaveClass($td.parent(), 'o_selected_row', "td should not be in edit mode");
        await testUtils.dom.click($td);
        assert.hasClass($td.parent(),'o_selected_row', "td should be in edit mode");
        list.destroy();
    });

    QUnit.test('editable list: add a line and discard', async function (assert) {
        assert.expect(11);

        testUtils.mock.patch(basicFields.FieldChar, {
            destroy: function () {
                assert.step('destroy');
                this._super.apply(this, arguments);
            },
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
            domain: [['foo', '=', 'yop']],
        });

        assert.containsN(list, 'tbody tr', 4,
            "list should contain 4 rows");
        assert.containsOnce(list, '.o_data_row',
            "list should contain one record (and thus 3 empty rows)");
        assert.strictEqual(list.pager.$('.o_pager_value').text(), '1-1',
            "pager should be correct");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.containsN(list, 'tbody tr', 4,
            "list should still contain 4 rows");
        assert.containsN(list, '.o_data_row', 2,
            "list should contain two record (and thus 2 empty rows)");
        assert.strictEqual(list.pager.$('.o_pager_value').text(), '1-2',
            "pager should be correct");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));

        assert.containsN(list, 'tbody tr', 4,
            "list should still contain 4 rows");
        assert.containsOnce(list, '.o_data_row',
            "list should contain one record (and thus 3 empty rows)");
        assert.strictEqual(list.pager.$('.o_pager_value').text(), '1-1',
            "pager should be correct");
        assert.verifySteps(['destroy'],
            "should have destroyed the widget of the removed line");

        testUtils.mock.unpatch(basicFields.FieldChar);
        list.destroy();
    });

    QUnit.test('field changes are triggered correctly', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });
        var $td = list.$('td:not(.o_list_record_selector)').first();

        var n = 0;
        testUtils.mock.intercept(list, "field_changed", function () {
            n += 1;
        });
        await testUtils.dom.click($td);
        testUtils.fields.editInput($td.find('input'), 'abc');
        assert.strictEqual(n, 1, "field_changed should have been triggered");
        await testUtils.dom.click(list.$('td:not(.o_list_record_selector)').eq(2));
        assert.strictEqual(n, 1, "field_changed should not have been triggered");
        list.destroy();
    });

    QUnit.test('editable list view: basic char field edition', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        var $td = list.$('td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($td);
        await testUtils.fields.editInput($td.find('input'), 'abc');
        assert.strictEqual($td.find('input').val(), 'abc', "char field has been edited correctly");

        var $next_row_td = list.$('tbody tr:eq(1) td:not(.o_list_record_selector)').first();
        await testUtils.dom.click($next_row_td);
        assert.strictEqual(list.$('td:not(.o_list_record_selector)').first().text(), 'abc',
            'changes should be saved correctly');
        assert.doesNotHaveClass(list.$('tbody tr').first(), 'o_selected_row',
            'saved row should be in readonly mode');
        assert.strictEqual(this.data.foo.records[0].foo, 'abc',
            "the edition should have been properly saved");
        list.destroy();
    });

    QUnit.test('editable list view: save data when list sorting in edit mode', async function (assert) {
        assert.expect(3);

        this.data.foo.fields.foo.sortable = true;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args, [[1], {foo: 'xyz'}],
                        "should correctly save the edited record");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$('.o_data_cell:first'));
        await testUtils.fields.editInput(list.$('input[name="foo"]'), 'xyz');
        await testUtils.dom.click(list.$('.o_column_sortable'));

        assert.hasClass(list.$('.o_data_row:first'),'o_selected_row',
            "first row should still be in edition");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.doesNotHaveClass(list.$buttons, 'o-editing',
            "list buttons should be back to their readonly mode");

        list.destroy();
    });

    QUnit.test('editable list view: check that controlpanel buttons are updating when groupby applied', async function (assert) {
        assert.expect(4);

        this.data.foo.fields.foo = {string: "Foo", type: "char", required:true};

        var actionManager = await createActionManager({
            actions: [{
               id: 11,
               name: 'Partners Action 11',
               res_model: 'foo',
               type: 'ir.actions.act_window',
               views: [[3, 'list']],
               search_view_id: [9, 'search'],
            }],
            archs:  {
               'foo,3,list': '<tree editable="top"><field name="display_name"/><field name="foo"/></tree>',

               'foo,9,search': '<search>'+
                                    '<filter string="candle" name="itsName" context="{\'group_by\': \'foo\'}"/>'  +
                                    '</search>',
            },
            data: this.data,
        });

        await actionManager.doAction(11);
        await testUtils.dom.click(actionManager.$('.o_list_button_add'));

        assert.isNotVisible(actionManager.$('.o_list_button_add'),
            "create button should be invisible");
        assert.isVisible(actionManager.$('.o_list_button_save'), "save button should be visible");

        await testUtils.dom.click(actionManager.$('.o_dropdown_toggler_btn:contains("Group By")'));
        await testUtils.dom.click(actionManager.$('.o_group_by_menu .o_menu_item a:contains("candle")'));

        assert.isNotVisible(actionManager.$('.o_list_button_add'), "create button should be invisible");
        assert.isNotVisible(actionManager.$('.o_list_button_save'),
            "save button should be invisible after applying groupby");

        actionManager.destroy();
    });

    QUnit.test('selection changes are triggered correctly', async function (assert) {
        assert.expect(8);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
        });
        var $tbody_selector = list.$('tbody .o_list_record_selector input').first();
        var $thead_selector = list.$('thead .o_list_record_selector input');

        var n = 0;
        testUtils.mock.intercept(list, "selection_changed", function () {
            n += 1;
        });

        // tbody checkbox click
        testUtils.dom.click($tbody_selector);
        assert.strictEqual(n, 1, "selection_changed should have been triggered");
        assert.ok($tbody_selector.is(':checked'), "selection checkbox should be checked");
        testUtils.dom.click($tbody_selector);
        assert.strictEqual(n, 2, "selection_changed should have been triggered");
        assert.ok(!$tbody_selector.is(':checked'), "selection checkbox shouldn't be checked");

        // head checkbox click
        testUtils.dom.click($thead_selector);
        assert.strictEqual(n, 3, "selection_changed should have been triggered");
        assert.containsN(list, 'tbody .o_list_record_selector input:checked',
            list.$('tbody tr').length, "all selection checkboxes should be checked");

        testUtils.dom.click($thead_selector);
        assert.strictEqual(n, 4, "selection_changed should have been triggered");

        assert.containsNone(list, 'tbody .o_list_record_selector input:checked',
                            "no selection checkbox should be checked");
        list.destroy();
    });

    QUnit.test('selection is reset on reload', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="int_field" sum="Sum"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('tfoot td:nth(2)').text(), '32',
            "total should be 32 (no record selected)");

        // select first record
        var $firstRowSelector = list.$('tbody .o_list_record_selector input').first();
        testUtils.dom.click($firstRowSelector);
        assert.ok($firstRowSelector.is(':checked'), "first row should be selected");
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), '10',
            "total should be 10 (first record selected)");

        // reload
        await list.reload();
        $firstRowSelector = list.$('tbody .o_list_record_selector input').first();
        assert.notOk($firstRowSelector.is(':checked'),
            "first row should no longer be selected");
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), '32',
            "total should be 32 (no more record selected)");

        list.destroy();
    });

    QUnit.test('selection is kept on render without reload', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            groupBy: ['foo'],
            viewOptions: {hasSidebar: true},
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="int_field" sum="Sum"/>' +
                '</tree>',
        });

        assert.isNotVisible(list.sidebar);

        // open blip grouping and check all lines
        await testUtils.dom.click(list.$('.o_group_header:contains("blip (2)")'));
        await testUtils.dom.click(list.$('.o_data_row:first input'));
        assert.isVisible(list.sidebar);

        // open yop grouping and verify blip are still checked
        await testUtils.dom.click(list.$('.o_group_header:contains("yop (1)")'));
        assert.containsOnce(list, '.o_data_row input:checked',
            "opening a grouping does not uncheck others");
        assert.isVisible(list.sidebar);

        // close and open blip grouping and verify blip are unchecked
        await testUtils.dom.click(list.$('.o_group_header:contains("blip (2)")'));
        await testUtils.dom.click(list.$('.o_group_header:contains("blip (2)")'));
        assert.containsNone(list, '.o_data_row input:checked',
            "opening and closing a grouping uncheck its elements");
        assert.isNotVisible(list.sidebar);

        list.destroy();
    });

    QUnit.test('aggregates are computed correctly', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field" sum="Sum"/></tree>',
        });
        var $tbody_selectors = list.$('tbody .o_list_record_selector input');
        var $thead_selector = list.$('thead .o_list_record_selector input');

        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "32", "total should be 32");

        testUtils.dom.click($tbody_selectors.first());
        testUtils.dom.click($tbody_selectors.last());
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "6",
                        "total should be 6 as first and last records are selected");

        testUtils.dom.click($thead_selector);
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "32",
                        "total should be 32 as all records are selected");

        // Let's update the view to dislay NO records
        await list.update({domain: ['&', ['bar', '=', false], ['int_field', '>', 0]]});
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "0", "total should have been recomputed to 0");

        list.destroy();
    });

    QUnit.test('aggregates are computed correctly in grouped lists', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            groupBy: ['m2o'],
            arch: '<tree editable="bottom"><field name="foo" /><field name="int_field" sum="Sum"/></tree>',
        });

        var $groupHeader1 = list.$('.o_group_header').filter(function (index, el) {
            return $(el).data('group').res_id === 1;
        });
        var $groupHeader2 = list.$('.o_group_header').filter(function (index, el) {
            return $(el).data('group').res_id === 2;
        });
        assert.strictEqual($groupHeader1.find('td:last()').text(), "23", "first group total should be 23");
        assert.strictEqual($groupHeader2.find('td:last()').text(), "9", "second group total should be 9");
        assert.strictEqual(list.$('tfoot td:last()').text(), "32", "total should be 32");

        await testUtils.dom.click($groupHeader1);
        await testUtils.dom.click(list.$('tbody .o_list_record_selector input').first());
        assert.strictEqual(list.$('tfoot td:last()').text(), "10",
                        "total should be 10 as first record of first group is selected");
        list.destroy();
    });

    QUnit.test('aggregates are updated when a line is edited', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="int_field" sum="Sum"/></tree>',
        });

        assert.strictEqual(list.$('td[title="Sum"]').text(), "32", "current total should be 32");

        await testUtils.dom.click(list.$('tr.o_data_row td.o_data_cell').first());
        await testUtils.fields.editInput(list.$('td.o_data_cell input'), "15");

        assert.strictEqual(list.$('td[title="Sum"]').text(), "37",
            "current total should now be 37");
        list.destroy();
    });

    QUnit.test('aggregates are formatted according to field widget', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="qux" widget="float_time" sum="Sum"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('tfoot td:nth(2)').text(), '19:24',
            "total should be formatted as a float_time");

        list.destroy();
    });

    QUnit.test('groups can be sorted on aggregates', async function (assert) {
        assert.expect(10);
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            groupBy: ['foo'],
            arch: '<tree editable="bottom"><field name="foo" /><field name="int_field" sum="Sum"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    assert.step(args.kwargs.orderby || 'default order');
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(list.$('tbody .o_list_number').text(), '10517',
            "initial order should be 10, 5, 17");
        assert.strictEqual(list.$('tfoot td:last()').text(), '32', "total should be 32");

        await testUtils.dom.click(list.$('.o_column_sortable'));
        assert.strictEqual(list.$('tfoot td:last()').text(), '32', "total should still be 32");
        assert.strictEqual(list.$('tbody .o_list_number').text(), '51017',
            "order should be 5, 10, 17");

        await testUtils.dom.click(list.$('.o_column_sortable'));
        assert.strictEqual(list.$('tbody .o_list_number').text(), '17105',
            "initial order should be 17, 10, 5");
        assert.strictEqual(list.$('tfoot td:last()').text(), '32', "total should still be 32");

        assert.verifySteps(['default order', 'int_field ASC', 'int_field DESC']);

        list.destroy();
    });

    QUnit.test('groups cannot be sorted on non-aggregable fields', async function (assert) {
        assert.expect(6);
        this.data.foo.fields.sort_field = {string: "sortable_field", type: "sting", sortable: true, default: "value"};
        _.each(this.data.records, function (elem) {
            elem.sort_field = "value" + elem.id;
        });
        this.data.foo.fields.foo.sortable = true;
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            groupBy: ['foo'],
            arch: '<tree editable="bottom"><field name="foo" /><field name="int_field"/><field name="sort_field"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    assert.step(args.kwargs.orderby || 'default order');
                }
                return this._super.apply(this, arguments);
            },
        });
        //we cannot sort by sort_field since it doesn't have a group_operator
        await testUtils.dom.click(list.$('.o_column_sortable:eq(2)'));
        //we can sort by int_field since it has a group_operator
        await testUtils.dom.click(list.$('.o_column_sortable:eq(1)'));
        //we keep previous order
        await testUtils.dom.click(list.$('.o_column_sortable:eq(2)'));
        //we can sort on foo since we are groupped by foo + previous order
        await testUtils.dom.click(list.$('.o_column_sortable:eq(0)'));

        assert.verifySteps([
            'default order',
            'default order',
            'int_field ASC',
            'int_field ASC',
            'foo ASC, int_field ASC'
        ]);

        list.destroy();
    });

    QUnit.test('properly apply onchange in simple case', async function (assert) {
        assert.expect(2);

        this.data.foo.onchanges = {
            foo: function (obj) {
                obj.int_field = obj.foo.length + 1000;
            },
        };
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="int_field"/></tree>',
        });

        var $foo_td = list.$('td:not(.o_list_record_selector)').first();
        var $int_field_td = list.$('td:not(.o_list_record_selector)').eq(1);

        assert.strictEqual($int_field_td.text(), '10', "should contain initial value");

        await testUtils.dom.click($foo_td);
        await testUtils.fields.editInput($foo_td.find('input'), 'tralala');

        assert.strictEqual($int_field_td.find('input').val(), "1007",
                        "should contain input with onchange applied");
        list.destroy();
    });

    QUnit.test('column width should not change when switching mode', async function (assert) {
        assert.expect(4);

        // Warning: this test is css dependant
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="foo"/>' +
                        '<field name="int_field" readonly="1"/>' +
                        '<field name="m2o"/>' +
                        '<field name="m2m" widget="many2many_tags"/>' +
                    '</tree>',
        });

        var startWidths = _.pluck(list.$('thead th'), 'offsetWidth');
        var startWidth = list.$('table').addBack('table').width();

        // start edition of first row
        await testUtils.dom.click(list.$('td:not(.o_list_record_selector)').first());

        var editionWidths = _.pluck(list.$('thead th'), 'offsetWidth');
        var editionWidth = list.$('table').addBack('table').width();

        // leave edition
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        var readonlyWidths = _.pluck(list.$('thead th'), 'offsetWidth');
        var readonlyWidth = list.$('table').addBack('table').width();

        assert.strictEqual(editionWidth, startWidth,
            "table should have kept the same width when switching from readonly to edit mode");
        assert.deepEqual(editionWidths, startWidths,
            "width of columns should remain unchanged when switching from readonly to edit mode");
        assert.strictEqual(readonlyWidth, editionWidth,
            "table should have kept the same width when switching from edit to readonly mode");
        assert.deepEqual(readonlyWidths, editionWidths,
            "width of columns should remain unchanged when switching from edit to readonly mode");

        list.destroy();
    });

    QUnit.test('row height should not change when switching mode', async function (assert) {
        // Warning: this test is css dependant
        assert.expect(3);

        var multiLang = _t.database.multi_lang;
        _t.database.multi_lang = true;

        this.data.foo.fields.foo.translate = true;
        this.data.foo.fields.boolean = {type: 'boolean', string: 'Bool'};
        var currencies = {};
        _.each(this.data.res_currency.records, function (currency) {
            currencies[currency.id] = currency;
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="foo" required="1"/>' +
                        '<field name="int_field" readonly="1"/>' +
                        '<field name="boolean"/>' +
                        '<field name="date"/>' +
                        '<field name="text" width_factor="2"/>' +
                        '<field name="amount"/>' +
                        '<field name="currency_id" invisible="1"/>' +
                        '<field name="m2o"/>' +
                        '<field name="m2m" widget="many2many_tags"/>' +
                    '</tree>',
            session: {
                currencies: currencies,
            },
        });
        var startHeight = list.$('.o_data_row:first').height();

        // start edition of first row
        await testUtils.dom.click(list.$('.o_data_row:first > td:not(.o_list_record_selector)').first());

        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');
        var editionHeight = list.$('.o_data_row:first').height();

        // leave edition
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        var readonlyHeight = list.$('.o_data_row:first').height();

        assert.strictEqual(startHeight, editionHeight);
        assert.strictEqual(startHeight, readonlyHeight);

        _t.database.multi_lang = multiLang;
        list.destroy();
    });

    QUnit.test('deleting one record', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {hasSidebar: true},
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.isNotVisible(list.sidebar.$el, 'sidebar should be invisible');
        assert.containsN(list, 'tbody td.o_list_record_selector', 4, "should have 4 records");

        await testUtils.dom.click(list.$('tbody td.o_list_record_selector:first input'));

        assert.isVisible(list.sidebar.$el, 'sidebar should be visible');

        await testUtils.dom.click(list.sidebar.$('.o_dropdown_toggler_btn:contains(Action)'));
        await testUtils.dom.click(list.sidebar.$('a:contains(Delete)'));
        assert.hasClass($('body'),'modal-open', 'body should have modal-open clsss');

        await testUtils.dom.click($('body .modal button span:contains(Ok)'));

        assert.containsN(list, 'tbody td.o_list_record_selector', 3, "should have 3 records");
        list.destroy();
    });

    QUnit.test('archiving one record', async function (assert) {
        assert.expect(12);

        // add active field on foo model and make all records active
        this.data.foo.fields.active = {string: 'Active', type: 'boolean', default: true};

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {hasSidebar: true},
            arch: '<tree><field name="foo"/></tree>',
            mockRPC: function (route) {
                assert.step(route);
                if (route === '/web/dataset/call_kw/foo/action_archive') {
                    this.data.foo.records[0].active = false;
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.isNotVisible(list.sidebar.$el, 'sidebar should be invisible');
        assert.containsN(list, 'tbody td.o_list_record_selector', 4, "should have 4 records");

        testUtils.dom.click(list.$('tbody td.o_list_record_selector:first input'));

        assert.isVisible(list.sidebar.$el, 'sidebar should be visible');

        assert.verifySteps(['/web/dataset/search_read']);
        testUtils.dom.click(list.sidebar.$('.o_dropdown_toggler_btn:contains(Action)'));
        await testUtils.dom.click(list.sidebar.$('a:contains(Archive)'));
        assert.strictEqual($('.modal').length, 1, 'a confirm modal should be displayed');
        testUtils.dom.click($('.modal-footer .btn-secondary'));
        assert.containsN(list, 'tbody td.o_list_record_selector', 4, "still should have 4 records");

        testUtils.dom.click(list.sidebar.$('.o_dropdown_toggler_btn:contains(Action)'));
        await testUtils.dom.click(list.sidebar.$('a:contains(Archive)'));
        assert.strictEqual($('.modal').length, 1, 'a confirm modal should be displayed');
        await testUtils.dom.click($('.modal-footer .btn-primary'));
        assert.containsN(list, 'tbody td.o_list_record_selector', 3, "should have 3 records");
        assert.verifySteps(['/web/dataset/call_kw/foo/action_archive', '/web/dataset/search_read']);
        list.destroy();
    });

    QUnit.test('pager (ungrouped and grouped mode), default limit', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.strictEqual(args.limit, 80, "default limit should be 80 in List");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.isVisible(list.pager.$el, "pager should be visible");
        assert.strictEqual(list.pager.state.size, 4, "pager's size should be 4");
        await list.update({ groupBy: ['bar']});
        assert.strictEqual(list.pager.state.size, 2, "pager's size should be 2");
        list.destroy();
    });

    QUnit.test('can sort records when clicking on header', async function (assert) {
        assert.expect(9);

        this.data.foo.fields.foo.sortable = true;

        var nbSearchRead = 0;
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            mockRPC: function (route) {
                if (route === '/web/dataset/search_read') {
                    nbSearchRead++;
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.ok(list.$('tbody tr:first td:contains(yop)').length,
            "record 1 should be first");
        assert.ok(list.$('tbody tr:eq(3) td:contains(blip)').length,
            "record 3 should be first");

        nbSearchRead = 0;
        await testUtils.dom.click(list.$('thead th:contains(Foo)'));
        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.ok(list.$('tbody tr:first td:contains(blip)').length,
            "record 3 should be first");
        assert.ok(list.$('tbody tr:eq(3) td:contains(yop)').length,
            "record 1 should be first");

        nbSearchRead = 0;
        await testUtils.dom.click(list.$('thead th:contains(Foo)'));
        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.ok(list.$('tbody tr:first td:contains(yop)').length,
            "record 3 should be first");
        assert.ok(list.$('tbody tr:eq(3) td:contains(blip)').length,
            "record 1 should be first");

        list.destroy();
    });

    QUnit.test('use default_order', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree default_order="foo"><field name="foo"/><field name="bar"/></tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.strictEqual(args.sort, 'foo ASC',
                        "should correctly set the sort attribute");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(list.$('tbody tr:first td:contains(blip)').length,
            "record 3 should be first");
        assert.ok(list.$('tbody tr:eq(3) td:contains(yop)').length,
            "record 1 should be first");

        list.destroy();
    });

    QUnit.test('use more complex default_order', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree default_order="foo, bar desc, int_field">' +
                    '<field name="foo"/><field name="bar"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.strictEqual(args.sort, 'foo ASC, bar DESC, int_field ASC',
                        "should correctly set the sort attribute");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(list.$('tbody tr:first td:contains(blip)').length,
            "record 3 should be first");
        assert.ok(list.$('tbody tr:eq(3) td:contains(yop)').length,
            "record 1 should be first");

        list.destroy();
    });

    QUnit.test('use default_order on editable tree: sort on save', async function (assert) {
        assert.expect(8);

        this.data.foo.records[0].o2m = [1, 3];

        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="o2m">' +
                            '<tree editable="bottom" default_order="display_name">' +
                                '<field name="display_name"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");

        var $o2m = form.$('.o_field_widget[name=o2m]');
        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        await testUtils.fields.editInput($o2m.find('.o_field_widget'), "Value 2");
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");
        assert.ok(form.$('tbody tr:eq(2) td input').val(),
            "Value 2 should be third (shouldn't be sorted)");

        await testUtils.form.clickSave(form);
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 2)').length,
            "Value 2 should be second (should be sorted after saving)");
        assert.ok(form.$('tbody tr:eq(2) td:contains(Value 3)').length,
            "Value 3 should be third");

        form.destroy();
    });

    QUnit.test('use default_order on editable tree: sort on demand', async function (assert) {
        assert.expect(11);

        this.data.foo.records[0].o2m = [1, 3];
        this.data.bar.fields = {name: {string: "Name", type: "char", sortable: true}};
        this.data.bar.records[0].name = "Value 1";
        this.data.bar.records[2].name = "Value 3";

        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="o2m">' +
                            '<tree editable="bottom" default_order="name">' +
                                '<field name="name"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");

        var $o2m = form.$('.o_field_widget[name=o2m]');
        await testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        await testUtils.fields.editInput($o2m.find('.o_field_widget'), "Value 2");
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");
        assert.ok(form.$('tbody tr:eq(2) td input').val(),
            "Value 2 should be third (shouldn't be sorted)");

        await testUtils.dom.click(form.$('.o_form_sheet_bg'));

        await testUtils.dom.click($o2m.find('.o_column_sortable'));
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 1',
            "Value 1 should be first");
        assert.strictEqual(form.$('tbody tr:eq(1)').text(), 'Value 2',
            "Value 2 should be second (should be sorted after saving)");
        assert.strictEqual(form.$('tbody tr:eq(2)').text(), 'Value 3',
            "Value 3 should be third");

        await testUtils.dom.click($o2m.find('.o_column_sortable'));
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 3',
            "Value 3 should be first");
        assert.strictEqual(form.$('tbody tr:eq(1)').text(), 'Value 2',
            "Value 2 should be second (should be sorted after saving)");
        assert.strictEqual(form.$('tbody tr:eq(2)').text(), 'Value 1',
            "Value 1 should be third");

        form.destroy();
    });

    QUnit.test('use default_order on editable tree: sort on demand in page', async function (assert) {
        assert.expect(4);

        this.data.bar.fields = {name: {string: "Name", type: "char", sortable: true}};

        var ids = [];
        for (var i=0; i<45; i++) {
            var id = 4 + i;
            ids.push(id);
            this.data.bar.records.push({
                id: id,
                name: "Value " + (id < 10 ? '0' : '') + id,
            });
        }
        this.data.foo.records[0].o2m = ids;

        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="o2m">' +
                            '<tree editable="bottom" default_order="name">' +
                                '<field name="name"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        // Change page
        await testUtils.dom.click(form.$('.o_field_widget[name=o2m] .o_pager_next'));
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 44',
            "record 44 should be first");
        assert.strictEqual(form.$('tbody tr:eq(4)').text(), 'Value 48',
            "record 48 should be last");

        await testUtils.dom.click(form.$('.o_column_sortable'));
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 08',
            "record 48 should be first");
        assert.strictEqual(form.$('tbody tr:eq(4)').text(), 'Value 04',
            "record 44 should be first");

        form.destroy();
    });

    QUnit.test('can display button in edit mode', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<button name="notafield" type="object" icon="fa-asterisk" class="o_yeah"/>' +
                '</tree>',
        });
        assert.containsN(list, 'tbody button[name=notafield]', 4);
        assert.containsN(list, 'tbody button[name=notafield].o_yeah', 4, "class o_yeah should be set on the four button");
        list.destroy();
    });

    QUnit.test('can display a list with a many2many field', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="m2m"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                assert.step(route);
                return this._super(route, args);
            },
        });
        assert.verifySteps(['/web/dataset/search_read'], "should have done 1 search_read");
        assert.ok(list.$('td:contains(3 records)').length,
            "should have a td with correct formatted value");
        list.destroy();
    });

    QUnit.test('list without import button', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            context: {
                group_by_no_leaf: true,
            }
        });

        assert.ok(!list.$buttons, "should not have any buttons");
        list.destroy();
    });

    QUnit.test('display a tooltip on a field', async function (assert) {
        assert.expect(4);

        var initialDebugMode = odoo.debug;
        odoo.debug = false;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="bar" widget="toggle_button"/>' +
                '</tree>',
        });

        // this is done to force the tooltip to show immediately instead of waiting
        // 1000 ms. not totally academic, but a short test suite is easier to sell :(
        list.$('th[data-name=foo]').tooltip('show', false);

        list.$('th[data-name=foo]').trigger($.Event('mouseenter'));
        assert.strictEqual($('.tooltip .oe_tooltip_string').length, 0, "should not have rendered a tooltip");

        odoo.debug = true;
        // it is necessary to rerender the list so tooltips can be properly created
        await list.reload();
        list.$('th[data-name=foo]').tooltip('show', false);
        list.$('th[data-name=foo]').trigger($.Event('mouseenter'));
        assert.strictEqual($('.tooltip .oe_tooltip_string').length, 1, "should have rendered a tooltip");

        await list.reload();
        list.$('th[data-name=bar]').tooltip('show', false);
        list.$('th[data-name=bar]').trigger($.Event('mouseenter'));
        assert.containsOnce($, '.oe_tooltip_technical>li[data-item="widget"]',
            'widget should be present for this field');
        assert.strictEqual($('.oe_tooltip_technical>li[data-item="widget"]')[0].lastChild.wholeText.trim(),
            'Button (toggle_button)', "widget description should be correct");

        odoo.debug = initialDebugMode;
        list.destroy();
    });

    QUnit.test('support row decoration', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree decoration-info="int_field > 5">' +
                    '<field name="foo"/><field name="int_field"/>' +
                '</tree>',
        });

        assert.containsN(list, 'tbody tr.text-info', 3,
            "should have 3 columns with text-info class");

        assert.containsN(list, 'tbody tr', 4, "should have 4 rows");
        list.destroy();
    });

    QUnit.test('support row decoration (with unset numeric values)', async function (assert) {
        assert.expect(2);

        this.data.foo.records = [];

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom" decoration-danger="int_field &lt; 0">' +
                    '<field name="int_field"/>' +
                '</tree>',
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.containsNone(list, 'tr.o_data_row.text-danger',
            "the data row should not have .text-danger decoration (int_field is unset)");
        await testUtils.fields.editInput(list.$('input[name="int_field"]'), '-3');
        assert.containsOnce(list, 'tr.o_data_row.text-danger',
            "the data row should have .text-danger decoration (int_field is negative)");
        list.destroy();
    });

    QUnit.test('support row decoration with date', async function (assert) {
        assert.expect(3);

        this.data.foo.records[0].datetime = '2017-02-27 12:51:35';

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree decoration-info="datetime == \'2017-02-27 12:51:35\'" decoration-danger="datetime &gt; \'2017-02-27 12:51:35\' AND datetime &lt; \'2017-02-27 10:51:35\'">' +
                    '<field name="datetime"/><field name="int_field"/>' +
                '</tree>',
        });

        assert.containsOnce(list, 'tbody tr.text-info',
            "should have 1 columns with text-info class with good datetime");

        assert.containsNone(list, 'tbody tr.text-danger',
            "should have 0 columns with text-danger class with wrong timezone datetime");

        assert.containsN(list, 'tbody tr', 4, "should have 4 rows");
        list.destroy();
    });

    QUnit.test('no content helper when no data', async function (assert) {
        assert.expect(5);

        var records = this.data.foo.records;

        this.data.foo.records = [];

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            viewOptions: {
                action: {
                    help: '<p class="hello">click to add a partner</p>'
                }
            },
        });

        assert.containsOnce(list, '.o_view_nocontent',
            "should display the no content helper");

        assert.containsNone(list, 'table', "should not have a table in the dom");

        assert.strictEqual(list.$('.o_view_nocontent p.hello:contains(add a partner)').length, 1,
            "should have rendered no content helper from action");

        this.data.foo.records = records;
        await list.reload();

        assert.containsNone(list, '.o_view_nocontent',
            "should not display the no content helper");
        assert.containsOnce(list, 'table', "should have a table in the dom");
        list.destroy();
    });

    QUnit.test('no nocontent helper when no data and no help', async function (assert) {
        assert.expect(3);

        this.data.foo.records = [];

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.containsNone(list, '.o_view_nocontent',
            "should not display the no content helper");

        assert.containsNone(list, 'tr.o_data_row',
            "should not have any data row");

        assert.containsOnce(list, 'table', "should have a table in the dom");
        list.destroy();
    });

    QUnit.test('groupby node with a button', async function (assert) {
        assert.expect(14);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                '<field name="foo"/>' +
                '<groupby name="currency_id">' +
                    '<button string="Button 1" type="object" name="button_method"/>' +
                '</groupby>' +
            '</tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            intercepts: {
                execute_action: function (ev) {
                    assert.deepEqual(ev.data.env.currentID, 2,
                        'should call with correct id');
                    assert.strictEqual(ev.data.env.model, 'res_currency',
                        'should call with correct model');
                    assert.strictEqual(ev.data.action_data.name, 'button_method',
                        "should call correct method");
                    assert.strictEqual(ev.data.action_data.type, 'object',
                        'should have correct type');
                    ev.data.on_success();
                },
            },
        });

        assert.verifySteps(['/web/dataset/search_read']);
        assert.containsOnce(list, 'thead th:not(.o_list_record_selector)',
            "there should be only one column");

        await list.update({groupBy: ['currency_id']});

        assert.verifySteps(['web_read_group']);
        assert.containsN(list, '.o_group_header', 2,
            "there should be 2 group headers");
        assert.containsNone(list, '.o_group_header button', 0,
            "there should be no button in the header");

        await testUtils.dom.click(list.$('.o_group_header:eq(0)'));
        assert.verifySteps(['/web/dataset/search_read']);
        assert.containsOnce(list, '.o_group_header button');

        await testUtils.dom.click(list.$('.o_group_header:eq(0) button'));

        list.destroy();
    });

    QUnit.test('groupby node with a button with modifiers', async function (assert) {
        assert.expect(11);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                '<field name="foo"/>' +
                '<groupby name="currency_id">' +
                    '<field name="position"/>' +
                    '<button string="Button 1" type="object" name="button_method" attrs=\'{"invisible": [("position", "=", "after")]}\'/>' +
                '</groupby>' +
            '</tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'read' && args.model === 'res_currency') {
                    assert.deepEqual(args.args, [[2, 1], ['position']]);
                }
                return this._super.apply(this, arguments);
            },
            groupBy: ['currency_id'],
        });

        assert.verifySteps(['web_read_group', 'read']);

        await testUtils.dom.click(list.$('.o_group_header:eq(0)'));

        assert.verifySteps(['/web/dataset/search_read']);
        assert.containsOnce(list, '.o_group_header button.o_invisible_modifier',
            "the first group (EUR) should have an invisible button");

        await testUtils.dom.click(list.$('.o_group_header:eq(1)'));

        assert.verifySteps(['/web/dataset/search_read']);
        assert.containsN(list, '.o_group_header button', 2,
            "there should be two buttons (one by header)");
        assert.doesNotHaveClass(list, '.o_group_header:eq(1) button', 'o_invisible_modifier',
            "the second header button should be visible");

        list.destroy();
    });

    QUnit.test('reload list view with groupby node', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree expand="1">' +
                '<field name="foo"/>' +
                '<groupby name="currency_id">' +
                    '<field name="position"/>' +
                    '<button string="Button 1" type="object" name="button_method" attrs=\'{"invisible": [("position", "=", "after")]}\'/>' +
                '</groupby>' +
            '</tree>',
            groupBy: ['currency_id'],
        });

        assert.containsOnce(list, '.o_group_header button:not(.o_invisible_modifier)',
            "there should be one visible button");

        await list.reload({ domain: [] });
        assert.containsOnce(list, '.o_group_header button:not(.o_invisible_modifier)',
            "there should still be one visible button");

        list.destroy();
    });

    QUnit.test('editable list view with groupby node and modifiers', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree expand="1" editable="bottom">' +
                '<field name="foo"/>' +
                '<groupby name="currency_id">' +
                    '<field name="position"/>' +
                    '<button string="Button 1" type="object" name="button_method" attrs=\'{"invisible": [("position", "=", "after")]}\'/>' +
                '</groupby>' +
            '</tree>',
            groupBy: ['currency_id'],
        });

        assert.doesNotHaveClass(list.$('.o_data_row:first'), 'o_selected_row',
            "first row should be in readonly mode");

        await testUtils.dom.click(list.$('.o_data_row:first .o_data_cell'));
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row',
            "the row should be in edit mode");

        await testUtils.fields.triggerKeydown($(document.activeElement), 'escape');
        assert.doesNotHaveClass(list.$('.o_data_row:first'), 'o_selected_row',
            "the row should be back in readonly mode");

        list.destroy();
    });

    QUnit.test('groupby node with edit button', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree expand="1">' +
                '<field name="foo"/>' +
                '<groupby name="currency_id">' +
                    '<button string="Button 1" type="edit" name="edit"/>' +
                '</groupby>' +
            '</tree>',
            groupBy: ['currency_id'],
            intercepts: {
                do_action: function (event) {
                    assert.deepEqual(event.data.action, {
                        res_id: 2,
                        res_model: 'res_currency',
                        type: 'ir.actions.act_window',
                        views: [[false, 'form']],
                        flags: {mode: 'edit'},
                    }, "should trigger do_action with correct action parameter");
                }
            },
        });
        await testUtils.dom.click(list.$('.o_group_header:eq(0) button'));
        list.destroy();
    });

    QUnit.test('list view, editable, without data', async function (assert) {
        assert.expect(12);

        this.data.foo.records = [];

        this.data.foo.fields.date.default = "2017-02-10";

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="date"/>' +
                    '<field name="m2o"/>' +
                    '<field name="foo"/>' +
                    '<button type="object" icon="fa-plus-square" name="method"/>' +
                '</tree>',
            viewOptions: {
                action: {
                    help: '<p class="hello">click to add a partner</p>'
                }
            },
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.ok(true, "should have created a record");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(list, '.o_view_nocontent',
            "should have a no content helper displayed");

        assert.containsNone(list, 'div.table-responsive',
            "should not have a div.table-responsive");
        assert.containsNone(list, 'table', "should not have rendered a table");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.containsNone(list, '.o_view_nocontent',
            "should not have a no content helper displayed");
        assert.containsOnce(list, 'table', "should have rendered a table");

        assert.hasClass(list.$('tbody tr:eq(0)'), 'o_selected_row',
            "the date field td should be in edit mode");
        assert.strictEqual(list.$('tbody tr:eq(0) td:eq(1)').text().trim(), "",
            "the date field td should not have any content");

        assert.strictEqual(list.$('tr.o_selected_row .o_list_record_selector input').prop('disabled'), true,
            "record selector checkbox should be disabled while the record is not yet created");
        assert.strictEqual(list.$('.o_list_button button').prop('disabled'), true,
            "buttons should be disabled while the record is not yet created");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        assert.strictEqual(list.$('tbody tr:eq(0) .o_list_record_selector input').prop('disabled'), false,
            "record selector checkbox should not be disabled once the record is created");
        assert.strictEqual(list.$('.o_list_button button').prop('disabled'), false,
            "buttons should not be disabled once the record is created");

        list.destroy();
    });

    QUnit.test('list view, editable, with a button', async function (assert) {
        assert.expect(1);

        this.data.foo.records = [];

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="foo"/>' +
                    '<button string="abc" icon="fa-phone" type="object" name="schedule_another_phonecall"/>' +
                '</tree>',
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.containsOnce(list, 'table button.o_icon_button i.fa-phone',
            "should have rendered a button");
        list.destroy();
    });

    QUnit.test('list view with a button without icon', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="foo"/>' +
                    '<button string="abc" type="object" name="schedule_another_phonecall"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('table button').first().text(), 'abc',
            "should have rendered a button with string attribute as label");
        list.destroy();
    });

    QUnit.test('list view, editable, can discard', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="foo"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('td:not(.o_list_record_selector) input').length, 0, "no input should be in the table");

        await testUtils.dom.click(list.$('tbody td:not(.o_list_record_selector):first'));
        assert.strictEqual(list.$('td:not(.o_list_record_selector) input').length, 1, "first cell should be editable");

        assert.ok(list.$buttons.find('.o_list_button_discard').is(':visible'),
            "discard button should be visible");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));

        assert.strictEqual(list.$('td:not(.o_list_record_selector) input').length, 0, "no input should be in the table");

        assert.ok(!list.$buttons.find('.o_list_button_discard').is(':visible'),
            "discard button should not be visible");
        list.destroy();
    });

    QUnit.test('editable list view, click on the list to save', async function (assert) {
        assert.expect(3);

        this.data.foo.fields.date.default = "2017-02-10";
        this.data.foo.records = [];

        var createCount = 0;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="date"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    createCount++;
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        await testUtils.dom.click(list.$('.o_list_view'));

        assert.strictEqual(createCount, 1, "should have created a record");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        await testUtils.dom.click(list.$('tfoot'));

        assert.strictEqual(createCount, 2, "should have created a record");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        await testUtils.dom.click(list.$('tbody tr').last());

        assert.strictEqual(createCount, 3, "should have created a record");
        list.destroy();
    });

    QUnit.test('click on a button in a list view', async function (assert) {
        assert.expect(9);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<button string="a button" name="button_action" icon="fa-car" type="object"/>' +
                '</tree>',
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
            intercepts: {
                execute_action: function (event) {
                    assert.deepEqual(event.data.env.currentID, 1,
                        'should call with correct id');
                    assert.strictEqual(event.data.env.model, 'foo',
                        'should call with correct model');
                    assert.strictEqual(event.data.action_data.name, 'button_action',
                        "should call correct method");
                    assert.strictEqual(event.data.action_data.type, 'object',
                        'should have correct type');
                    event.data.on_closed();
                },
            },
        });

        assert.containsN(list, '.o_list_button', 4,
            "there should be one button per row");
        assert.containsOnce(list, '.o_list_button:first .o_icon_button .fa.fa-car',
            'buttons should have correct icon');

        await testUtils.dom.click(list.$('.o_list_button:first > button'));
        assert.verifySteps(['/web/dataset/search_read', '/web/dataset/search_read'],
            "should have reloaded the view (after the action is complete)");
        list.destroy();
    });

    QUnit.test('invisible attrs in readonly and editable list', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<button string="a button" name="button_action" icon="fa-car" ' +
                        'type="object" attrs="{\'invisible\': [(\'id\',\'=\', 1)]}"/>' +
                    '<field name="int_field"/>' +
                    '<field name="qux"/>' +
                    '<field name="foo" attrs="{\'invisible\': [(\'id\',\'=\', 1)]}"/>' +
                '</tree>',
        });

        assert.equal(list.$('tbody tr:nth(0) td:nth(4)').html(), "",
            "td that contains an invisible field should be empty");
        assert.equal(list.$('tbody tr:nth(0) td:nth(1)').html(), "",
            "td that contains an invisible button should be empty");

        // edit first row
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2)'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(4) input.o_invisible_modifier').length, 1,
            "td that contains an invisible field should not be empty in edition");
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > button.o_invisible_modifier').length, 1,
            "td that contains an invisible button should not be empty in edition");
        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));

        // click on the invisible field's cell to edit first row
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(4)'));
        assert.hasClass(list.$('tbody tr:nth(0)'),'o_selected_row',
            "first row should be in edition");
        list.destroy();
    });

    QUnit.test('monetary fields are properly rendered', async function (assert) {
        assert.expect(3);

        var currencies = {};
        _.each(this.data.res_currency.records, function (currency) {
            currencies[currency.id] = currency;
        });
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="id"/>' +
                    '<field name="amount"/>' +
                    '<field name="currency_id" invisible="1"/>' +
                '</tree>',
            session: {
                currencies: currencies,
            },
        });

        assert.containsN(list, 'tbody tr:first td', 3,
            "currency_id column should not be in the table");
        assert.strictEqual(list.$('tbody tr:first td:nth(2)').text().replace(/\s/g, ' '),
            '1200.00 €', "currency_id column should not be in the table");
        assert.strictEqual(list.$('tbody tr:nth(1) td:nth(2)').text().replace(/\s/g, ' '),
            '$ 500.00', "currency_id column should not be in the table");

        list.destroy();
    });

    QUnit.test('simple list with date and datetime', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="date"/><field name="datetime"/></tree>',
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
        });

        assert.strictEqual(list.$('td:eq(1)').text(), "01/25/2017",
            "should have formatted the date");
        assert.strictEqual(list.$('td:eq(2)').text(), "12/12/2016 12:55:05",
            "should have formatted the datetime");
        list.destroy();
    });

    QUnit.test('edit a row by clicking on a readonly field', async function (assert) {
        assert.expect(9);

        this.data.foo.fields.foo.readonly = true;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
        });

        assert.hasClass(list.$('.o_data_row:first td:nth(1)'),'o_readonly_modifier',
            "foo field cells should have class 'o_readonly_modifier'");

        // edit the first row
        await testUtils.dom.click(list.$('.o_data_row:first td:nth(1)'));
        assert.hasClass(list.$('.o_data_row:first'),'o_selected_row',
            "first row should be selected");
        var $cell = list.$('.o_data_row:first td:nth(1)');
        // review
        assert.hasClass($cell, 'o_readonly_modifier');
        assert.hasClass($cell.parent(),'o_selected_row');
        assert.strictEqual(list.$('.o_data_row:first td:nth(1) span').text(), 'yop',
            "a widget should have been rendered for readonly fields");
        assert.hasClass(list.$('.o_data_row:first td:nth(2)').parent(),'o_selected_row',
            "field 'int_field' should be in edition");
        assert.strictEqual(list.$('.o_data_row:first td:nth(2) input').length, 1,
            "a widget for field 'int_field should have been rendered'");

        // click again on readonly cell of first line: nothing should have changed
        await testUtils.dom.click(list.$('.o_data_row:first td:nth(1)'));
        assert.hasClass(list.$('.o_data_row:first'),'o_selected_row',
            "first row should be selected");
        assert.strictEqual(list.$('.o_data_row:first td:nth(2) input').length, 1,
            "a widget for field 'int_field' should have been rendered (only once)");

        list.destroy();
    });

    QUnit.test('list view with nested groups', async function (assert) {
        assert.expect(42);

        this.data.foo.records.push({id: 5, foo: "blip", int_field: -7, m2o: 1});
        this.data.foo.records.push({id: 6, foo: "blip", int_field: 5, m2o: 2});

        var nbRPCs = {readGroup: 0, searchRead: 0};
        var envIDs = []; // the ids that should be in the environment during this test

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="id"/><field name="int_field"/></tree>',
            groupBy: ['m2o', 'foo'],
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    if (args.kwargs.groupby[0] === 'foo') { // nested read_group
                        // called twice (once when opening the group, once when sorting)
                        assert.deepEqual(args.kwargs.domain, [['m2o', '=', 1]],
                            "nested read_group should be called with correct domain");
                    }
                    nbRPCs.readGroup++;
                } else if (route === '/web/dataset/search_read') {
                    // called twice (once when opening the group, once when sorting)
                    assert.deepEqual(args.domain, [['foo', '=', 'blip'], ['m2o', '=', 1]],
                        "nested search_read should be called with correct domain");
                    nbRPCs.searchRead++;
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                switch_view: function (event) {
                    assert.strictEqual(event.data.res_id, 4,
                        "'switch_view' event has been triggered");
                },
            },
        });

        assert.strictEqual(nbRPCs.readGroup, 1, "should have done one read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        // basic rendering tests
        assert.containsOnce(list, 'tbody', "there should be 1 tbody");
        assert.containsN(list, '.o_group_header', 2,
            "should contain 2 groups at first level");
        assert.strictEqual(list.$('.o_group_name:first').text(), 'Value 1 (4)',
            "group should have correct name and count");
        assert.containsN(list, '.o_group_name .fa-caret-right', 2,
            "the carret of closed groups should be right");
        assert.strictEqual(list.$('.o_group_name:first span').css('padding-left'),
            '0px', "groups of level 1 should have a 0px padding-left");
        assert.strictEqual(list.$('.o_group_header:first td:last').text(), '16',
            "group aggregates are correctly displayed");

        // open the first group
        nbRPCs = {readGroup: 0, searchRead: 0};
        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.strictEqual(nbRPCs.readGroup, 1, "should have done one read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        var $openGroup = list.$('tbody:nth(1)');
        assert.strictEqual(list.$('.o_group_name:first').text(), 'Value 1 (4)',
            "group should have correct name and count (of records, not inner subgroups)");
        assert.containsN(list, 'tbody', 3, "there should be 3 tbodys");
        assert.containsOnce(list, '.o_group_name:first .fa-caret-down',
            "the carret of open groups should be down");
        assert.strictEqual($openGroup.find('.o_group_header').length, 3,
            "open group should contain 3 groups");
        assert.strictEqual($openGroup.find('.o_group_name:nth(2)').text(), 'blip (2)',
            "group should have correct name and count");
        assert.strictEqual($openGroup.find('.o_group_name:nth(2) span').css('padding-left'),
            '20px', "groups of level 2 should have a 20px padding-left");
        assert.strictEqual($openGroup.find('.o_group_header:nth(2) td:last').text(), '-11',
            "inner group aggregates are correctly displayed");

        // open subgroup
        nbRPCs = {readGroup: 0, searchRead: 0};
        envIDs = [4, 5]; // the opened subgroup contains these two records
        await testUtils.dom.click($openGroup.find('.o_group_header:nth(2)'));
        assert.strictEqual(nbRPCs.readGroup, 0, "should have done no read_group");
        assert.strictEqual(nbRPCs.searchRead, 1, "should have done one search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        var $openSubGroup = list.$('tbody:nth(2)');
        assert.containsN(list, 'tbody', 4, "there should be 4 tbodys");
        assert.strictEqual($openSubGroup.find('.o_data_row').length, 2,
            "open subgroup should contain 2 data rows");
        assert.strictEqual($openSubGroup.find('.o_data_row:first td:last').text(), '-4',
            "first record in open subgroup should be res_id 4 (with int_field -4)");

        // open a record (should trigger event 'open_record')
        await testUtils.dom.click($openSubGroup.find('.o_data_row:first'));

        // sort by int_field (ASC) and check that open groups are still open
        nbRPCs = {readGroup: 0, searchRead: 0};
        envIDs = [5, 4]; // order of the records changed
        await testUtils.dom.click(list.$('thead th:last'));
        assert.strictEqual(nbRPCs.readGroup, 2, "should have done two read_groups");
        assert.strictEqual(nbRPCs.searchRead, 1, "should have done one search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        $openSubGroup = list.$('tbody:nth(2)');
        assert.containsN(list, 'tbody', 4, "there should be 4 tbodys");
        assert.strictEqual($openSubGroup.find('.o_data_row').length, 2,
            "open subgroup should contain 2 data rows");
        assert.strictEqual($openSubGroup.find('.o_data_row:first td:last').text(), '-7',
            "first record in open subgroup should be res_id 5 (with int_field -7)");

        // close first level group
        nbRPCs = {readGroup: 0, searchRead: 0};
        envIDs = []; // the group being closed, there is no more record in the environment
        await testUtils.dom.click(list.$('.o_group_header:nth(1)'));
        assert.strictEqual(nbRPCs.readGroup, 0, "should have done no read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");
        assert.deepEqual(list.exportState().resIds, envIDs);

        assert.containsOnce(list, 'tbody', "there should be 1 tbody");
        assert.containsN(list, '.o_group_header', 2,
            "should contain 2 groups at first level");
        assert.containsN(list, '.o_group_name .fa-caret-right', 2,
            "the carret of closed groups should be right");

        list.destroy();
    });

    QUnit.test('grouped list on selection field at level 2', async function (assert) {
        assert.expect(4);

        this.data.foo.fields.priority = {
            string: "Priority",
            type: "selection",
            selection: [[1, "Low"], [2, "Medium"], [3, "High"]],
            default: 1,
        };
        this.data.foo.records.push({id: 5, foo: "blip", int_field: -7, m2o: 1, priority: 2});
        this.data.foo.records.push({id: 6, foo: "blip", int_field: 5, m2o: 1, priority: 3});

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="id"/><field name="int_field"/></tree>',
            groupBy: ['m2o', 'priority'],
        });

        assert.containsN(list, '.o_group_header', 2,
            "should contain 2 groups at first level");

        // open the first group
        await testUtils.dom.click(list.$('.o_group_header:first'));

        var $openGroup = list.$('tbody:nth(1)');
        assert.strictEqual($openGroup.find('tr').length, 3,
            "should have 3 subgroups");
        assert.strictEqual($openGroup.find('tr').length, 3,
            "should have 3 subgroups");
        assert.strictEqual($openGroup.find('.o_group_name:first').text(), 'Low (3)',
            "should display the selection name in the group header");

        list.destroy();
    });

    QUnit.test('grouped list with a pager in a group', async function (assert) {
        assert.expect(6);
        this.data.foo.records[3].bar = true;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
            viewOptions: {
                limit: 3,
            },
        });

        var headerHeight = list.$('.o_group_header').css('height');

        // basic rendering checks
        await testUtils.dom.click(list.$('.o_group_header'));
        assert.strictEqual(list.$('.o_group_header').css('height'), headerHeight,
            "height of group header shouldn't have changed");
        assert.hasClass(list.$('.o_group_header th'), 'o_group_pager',
            "last cell of open group header should have classname 'o_group_header'");
        assert.strictEqual(list.$('.o_group_header .o_pager_value').text(), '1-3',
            "pager's value should be correct");
        assert.containsN(list, '.o_data_row', 3,
            "open group should display 3 records");

        // go to next page
        await testUtils.dom.click(list.$('.o_group_header .o_pager_next'));
        assert.strictEqual(list.$('.o_group_header .o_pager_value').text(), '4-4',
            "pager's value should be correct");
        assert.containsOnce(list, '.o_data_row',
            "open group should display 1 record");

        list.destroy();
    });

    QUnit.test('edition: create new line, then discard', async function (assert) {
        assert.expect(8);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.containsN(list, 'tr.o_data_row', 4,
            "should have 4 records");
        assert.strictEqual(list.$buttons.find('.o_list_button_add:visible').length, 1,
            "create button should be visible");
        assert.strictEqual(list.$buttons.find('.o_list_button_discard:visible').length, 0,
            "discard button should be hidden");
        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        assert.strictEqual(list.$buttons.find('.o_list_button_add:visible').length, 0,
            "create button should be hidden");
        assert.strictEqual(list.$buttons.find('.o_list_button_discard:visible').length, 1,
            "discard button should be visible");
        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        assert.containsN(list, 'tr.o_data_row', 4,
            "should still have 4 records");
        assert.strictEqual(list.$buttons.find('.o_list_button_add:visible').length, 1,
            "create button should be visible again");
        assert.strictEqual(list.$buttons.find('.o_list_button_discard:visible').length, 0,
            "discard button should be hidden again");
        list.destroy();
    });

    QUnit.test('invisible attrs on fields are re-evaluated on field change', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="top">' +
                    '<field name="foo" attrs="{\'invisible\': [[\'bar\', \'=\', True]]}"/>' +
                    '<field name="bar"/>' +
                '</tree>',
        });

        assert.containsN(list, 'tbody td.o_invisible_modifier', 3,
            "there should be 3 invisible foo cells in readonly mode");

        // Make first line editable
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(1)'));

        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_invisible_modifier').length, 1,
            "the foo field widget should have been rendered as invisible");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]:not(.o_invisible_modifier)').length, 1,
            "the foo field widget should have been marked as non-invisible");
        assert.containsN(list, 'tbody td.o_invisible_modifier', 2,
            "the foo field widget parent cell should not be invisible anymore");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_invisible_modifier').length, 1,
            "the foo field widget should have been marked as invisible again");
        assert.containsN(list, 'tbody td.o_invisible_modifier', 3,
            "the foo field widget parent cell should now be invisible again");

        // Reswitch the cell to editable and save the row
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        await testUtils.dom.click(list.$('thead'));

        assert.containsN(list, 'tbody td.o_invisible_modifier', 2,
            "there should be 2 invisible foo cells in readonly mode");

        list.destroy();
    });

    QUnit.test('readonly attrs on fields are re-evaluated on field change', async function (assert) {
        assert.expect(9);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="top">' +
                    '<field name="foo" attrs="{\'readonly\': [[\'bar\', \'=\', True]]}"/>' +
                    '<field name="bar"/>' +
                '</tree>',
        });

        assert.containsN(list, 'tbody td.o_readonly_modifier', 3,
            "there should be 3 readonly foo cells in readonly mode");

        // Make first line editable
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(1)'));

        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > span[name="foo"]').length, 1,
            "the foo field widget should have been rendered as readonly");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]').length, 1,
            "the foo field widget should have been rerendered as editable");
        assert.containsN(list, 'tbody td.o_readonly_modifier', 2,
            "the foo field widget parent cell should not be readonly anymore");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > span[name="foo"]').length, 1,
            "the foo field widget should have been rerendered as readonly");
        assert.containsN(list, 'tbody td.o_readonly_modifier', 3,
            "the foo field widget parent cell should now be readonly again");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]').length, 1,
            "the foo field widget should have been rerendered as editable again");
        assert.containsN(list, 'tbody td.o_readonly_modifier', 2,
            "the foo field widget parent cell should not be readonly again");

        // Click outside to leave edition mode
        await testUtils.dom.click(list.$el);

        assert.containsN(list, 'tbody td.o_readonly_modifier', 2,
            "there should be 2 readonly foo cells in readonly mode");

        list.destroy();
    });

    QUnit.test('required attrs on fields are re-evaluated on field change', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="top">' +
                    '<field name="foo" attrs="{\'required\': [[\'bar\', \'=\', True]]}"/>' +
                    '<field name="bar"/>' +
                '</tree>',
        });

        assert.containsN(list, 'tbody td.o_required_modifier', 3,
            "there should be 3 required foo cells in readonly mode");

        // Make first line editable
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(1)'));

        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_required_modifier').length, 1,
            "the foo field widget should have been rendered as required");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]:not(.o_required_modifier)').length, 1,
            "the foo field widget should have been marked as non-required");
        assert.containsN(list, 'tbody td.o_required_modifier', 2,
            "the foo field widget parent cell should not be required anymore");

        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_required_modifier').length, 1,
            "the foo field widget should have been marked as required again");
        assert.containsN(list, 'tbody td.o_required_modifier', 3,
            "the foo field widget parent cell should now be required again");

        // Reswitch the cell to editable and save the row
        await testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        await testUtils.dom.click(list.$('thead'));

        assert.containsN(list, 'tbody td.o_required_modifier', 2,
            "there should be 2 required foo cells in readonly mode");

        list.destroy();
    });

    QUnit.test('leaving unvalid rows in edition', async function (assert) {
        assert.expect(4);

        var warnings = 0;
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="bottom">' +
                    '<field name="foo" required="1"/>' +
                    '<field name="bar"/>' +
                '</tree>',
            services: {
                notification: NotificationService.extend({
                    notify: function (params) {
                        if (params.type === 'danger') {
                            warnings++;
                        }
                    }
                }),
            },
        });

        // Start first line edition
        var $firstFooTd = list.$('tbody tr:nth(0) td:nth(1)');
        await testUtils.dom.click($firstFooTd);

        // Remove required foo field value
        await testUtils.fields.editInput($firstFooTd.find('input'), "");

        // Try starting other line edition
        var $secondFooTd = list.$('tbody tr:nth(1) td:nth(1)');
        await testUtils.dom.click($secondFooTd);
        await testUtils.nextTick();

        assert.strictEqual($firstFooTd.parent('.o_selected_row').length, 1,
            "first line should still be in edition as invalid");
        assert.containsOnce(list, 'tbody tr.o_selected_row',
            "no other line should be in edition");
        assert.strictEqual($firstFooTd.find('input.o_field_invalid').length, 1,
            "the required field should be marked as invalid");
        assert.strictEqual(warnings, 1,
            "a warning should have been displayed");

        list.destroy();
    });

    QUnit.test('open a virtual id', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'event',
            data: this.data,
            arch: '<tree><field name="name"/></tree>',
        });

        testUtils.mock.intercept(list, 'switch_view', function (event) {
            assert.deepEqual(_.pick(event.data, 'mode', 'model', 'res_id', 'view_type'), {
                mode: 'readonly',
                model: 'event',
                res_id: '2-20170808020000',
                view_type: 'form',
            }, "should trigger a switch_view event to the form view for the record virtual id");
        });
        testUtils.dom.click(list.$('td:contains(virtual)'));

        list.destroy();
    });

    QUnit.test('pressing enter on last line of editable list view', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });

        // click on 3rd line
        await testUtils.dom.click(list.$('td:contains(gnap)'));
        assert.hasClass(list.$('tr.o_data_row:eq(2)'),'o_selected_row',
            "3rd row should be selected");

        // press enter in input
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input'), 'enter');
        assert.hasClass(list.$('tr.o_data_row:eq(3)'),'o_selected_row',
            "4rd row should be selected");
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row',
            "3rd row should no longer be selected");

        // press enter on last row
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input'), 'enter');
        assert.containsN(list, 'tr.o_data_row', 5, "should have created a 5th row");

        assert.verifySteps(['/web/dataset/search_read', '/web/dataset/call_kw/foo/default_get']);
        list.destroy();
    });

    QUnit.test('pressing tab on last cell of editable list view', async function (assert) {
        assert.expect(9);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$('td:contains(blip)').last());
        assert.strictEqual(document.activeElement.name, "foo",
            "focus should be on an input with name = foo");

        //it will not create a new line unless a modification is made
        document.activeElement.value = "blip-changed";
        $(document.activeElement).trigger({type: 'change'});

        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');
        assert.strictEqual(document.activeElement.name, "int_field",
            "focus should be on an input with name = int_field");

        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');
        assert.hasClass(list.$('tr.o_data_row:eq(4)'),'o_selected_row',
            "5th row should be selected");
        assert.strictEqual(document.activeElement.name, "foo",
            "focus should be on an input with name = foo");

        assert.verifySteps(['/web/dataset/search_read',
            '/web/dataset/call_kw/foo/write',
            '/web/dataset/call_kw/foo/read',
            '/web/dataset/call_kw/foo/default_get']);
        list.destroy();
    });

    QUnit.test('navigation with tab and read completes after default_get', async function (assert) {
        assert.expect(8);

        var defaultGetPromise = testUtils.makeTestPromise();
        var readPromise = testUtils.makeTestPromise();

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
            mockRPC: function (route, args) {
                if (args.method) {
                    assert.step(args.method);
                }
                var result = this._super.apply(this, arguments);
                if (args.method === 'read') {
                    return readPromise.then(function () {
                        return result;
                    });
                }
                if (args.method === 'default_get') {
                    return defaultGetPromise.then(function () {
                        return result;
                    });
                }
                return result;
            },
        });

        await testUtils.dom.click(list.$('td:contains(-4)').last());

        await testUtils.fields.editInput(list.$('tr.o_selected_row input[name="int_field"]'), '1234');
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="int_field"]'), 'tab');

        defaultGetPromise.resolve();
        assert.containsN(list, 'tbody tr.o_data_row', 4,
            "should have 4 data rows");

        readPromise.resolve();
        await testUtils.nextTick();
        assert.containsN(list, 'tbody tr.o_data_row', 5,
            "should have 5 data rows");
        assert.strictEqual(list.$('td:contains(1234)').length, 1,
            "should have a cell with new value");

        // we trigger a tab to move to the second cell in the current row. this
        // operation requires that this.currentRow is properly set in the
        // list editable renderer.
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');
        assert.hasClass(list.$('tr.o_data_row:eq(4)'),'o_selected_row',
            "5th row should be selected");

        assert.verifySteps(['write', 'read', 'default_get']);
        list.destroy();
    });

    QUnit.test('display toolbar', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'event',
            data: this.data,
            arch: '<tree><field name="name"/></tree>',
            toolbar: {
                action: [{
                    model_name: 'event',
                    name: 'Action event',
                    type: 'ir.actions.server',
                    usage: 'ir_actions_server',
                }],
                print: [],
            },
            viewOptions: {
                hasSidebar: true,
            },
        });

        var $printMenu = list.$('.o_cp_sidebar .o_dropdown:contains(Print)');
        assert.isNotVisible($printMenu);
        var $actionMenu = list.$('.o_cp_sidebar .o_dropdown:contains(Action)');
        assert.isNotVisible($actionMenu);

        testUtils.dom.click(list.$('.o_list_record_selector:first input'));

        assert.isNotVisible($printMenu);
        assert.isVisible($actionMenu);

        testUtils.dom.click($actionMenu.find('button')); // open Action menu
        assert.strictEqual($actionMenu.find('.dropdown-item').length, 3,
            "there should be 3 actions");
        var $customAction = $actionMenu.find('.dropdown-item:last');
        assert.strictEqual($customAction.text().trim(), 'Action event',
            "the custom action should have 'Action event' as name");

        list.destroy();
    });

    QUnit.test('edit list line after line deletion', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="int_field"/></tree>',
        });

        await testUtils.dom.click(list.$('.o_data_row:nth(2) > td:not(.o_list_record_selector)').first());
        assert.ok(list.$('.o_data_row:nth(2)').is('.o_selected_row'),
            "third row should be in edition");
        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        assert.ok(list.$('.o_data_row:nth(0)').is('.o_selected_row'),
            "first row should be in edition (creation)");
        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        assert.containsNone(list, '.o_selected_row',
            "no row should be selected");
        await testUtils.dom.click(list.$('.o_data_row:nth(2) > td:not(.o_list_record_selector)').first());
        assert.ok(list.$('.o_data_row:nth(2)').is('.o_selected_row'),
            "third row should be in edition");
        assert.containsOnce(list, '.o_selected_row',
            "no other row should be selected");

        list.destroy();
    });

    QUnit.test('pressing TAB in editable list with several fields [REQUIRE FOCUS]', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                '</tree>',
        });

        await testUtils.dom.click(list.$('.o_data_cell:first'));
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:first .o_data_cell:first input')[0]);

        // Press 'Tab' -> should go to next cell (still in first row)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:first .o_data_cell:last input')[0]);

        // Press 'Tab' -> should go to next line (first cell)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(1) .o_data_cell:first input')[0]);

        list.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable list with several fields [REQUIRE FOCUS]', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                '</tree>',
        });

        await testUtils.dom.click(list.$('.o_data_row:nth(2) .o_data_cell:nth(1)'));
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(2) .o_data_cell:last input')[0]);

        // Press 'shift-Tab' -> should go to previous line (last cell)
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(2) .o_data_cell:first input')[0]);

        // Press 'shift-Tab' -> should go to previous cell
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(1) .o_data_cell:last input')[0]);

        list.destroy();
    });

    QUnit.test('navigation with tab and readonly field (no modification)', async function (assert) {
        // This test makes sure that if we have 2 cells in a row, the first in
        // edit mode, and the second one readonly, then if we press TAB when the
        // focus is on the first, then the focus skip the readonly cells and
        // directly goes to the next line instead.
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
        });

        // click on first td and press TAB
        await testUtils.dom.click(list.$('td:contains(yop)').last());

        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');

        assert.hasClass(list.$('tr.o_data_row:eq(1)'),'o_selected_row',
            "2nd row should be selected");

        // we do it again. This was broken because the this.currentRow variable
        // was not properly set, and the second TAB could cause a crash.
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');
        assert.hasClass(list.$('tr.o_data_row:eq(2)'),'o_selected_row',
            "3rd row should be selected");

        list.destroy();
    });

    QUnit.test('navigation with tab and readonly field (with modification)', async function (assert) {
        // This test makes sure that if we have 2 cells in a row, the first in
        // edit mode, and the second one readonly, then if we press TAB when the
        // focus is on the first, then the focus skips the readonly cells and
        // directly goes to the next line instead.
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
        });

        // click on first td and press TAB
        await testUtils.dom.click(list.$('td:contains(yop)'));

        //modity the cell content
        testUtils.fields.editAndTrigger($(document.activeElement),
            'blip-changed', ['change']);

        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');

        assert.hasClass(list.$('tr.o_data_row:eq(1)'),'o_selected_row',
            "2nd row should be selected");

        // we do it again. This was broken because the this.currentRow variable
        // was not properly set, and the second TAB could cause a crash.
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');
        assert.hasClass(list.$('tr.o_data_row:eq(2)'),'o_selected_row',
            "3rd row should be selected");

        list.destroy();
    });

    QUnit.test('navigation with tab on a list with create="0"', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom" create="0">' +
                        '<field name="display_name"/>' +
                    '</tree>',
        });

        assert.containsN(list, '.o_data_row', 4,
            "the list should contain 4 rows");

        await testUtils.dom.click(list.$('.o_data_row:nth(2) .o_data_cell:first'));
        assert.hasClass(list.$('.o_data_row:nth(2)'),'o_selected_row',
            "third row should be in edition");

        // Press 'Tab' -> should go to next line
        // add a value in the cell because the Tab on an empty first cell would activate the next widget in the view
        await testUtils.fields.editInput(list.$('.o_selected_row input').eq(1), 11);
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(3)'),'o_selected_row',
            "fourth row should be in edition");

        // Press 'Tab' -> should go back to first line as the create action isn't available
        await testUtils.fields.editInput(list.$('.o_selected_row input').eq(1), 11);
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:first'),'o_selected_row',
            "first row should be in edition");

        list.destroy();
    });

    QUnit.test('navigation with tab on a one2many list with create="0"', async function (assert) {
        assert.expect(4);

        this.data.foo.records[0].o2m = [1, 2];
        var form = await createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form><sheet>' +
                    '<field name="o2m">' +
                        '<tree editable="bottom" create="0">' +
                            '<field name="display_name"/>' +
                        '</tree>' +
                    '</field>' +
                    '<field name="foo"/>' +
                '</sheet></form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.containsN(form, '.o_field_widget[name=o2m] .o_data_row', 2,
            "there should be two records in the many2many");

        await testUtils.dom.click(form.$('.o_field_widget[name=o2m] .o_data_cell:first'));
        assert.hasClass(form.$('.o_field_widget[name=o2m] .o_data_row:first'),'o_selected_row',
            "first row should be in edition");

        // Press 'Tab' -> should go to next line
        await testUtils.fields.triggerKeydown(form.$('.o_field_widget[name=o2m] .o_selected_row input'), 'tab');
        assert.hasClass(form.$('.o_field_widget[name=o2m] .o_data_row:nth(1)'),'o_selected_row',
            "second row should be in edition");

        // Press 'Tab' -> should get out of the one to many and go to the next field of the form
        await testUtils.fields.triggerKeydown(form.$('.o_field_widget[name=o2m] .o_selected_row input'), 'tab');
        assert.strictEqual(document.activeElement, form.$('input[name="foo"]')[0],
            "the next field should be selected");

        form.destroy();
    });

    QUnit.test('navigation with tab in editable list with only readonly fields', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="m2o" attrs="{\'readonly\': [(\'int_field\', \'>\', 9)]}"/>' +
                    '<field name="int_field" readonly="1"/>' +
                '</tree>',
        });

        assert.hasClass(list.$('.o_data_row:first .o_data_cell:first'), 'o_readonly_modifier');
        assert.doesNotHaveClass(list.$('.o_data_row:nth(1) .o_data_cell:first'), 'o_readonly_modifier');

        // try to enter first row in edition
        await testUtils.dom.click(list.$('.o_data_row .o_data_cell:first'));

        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_selected_row .o_field_widget[name=m2o]').get(0));

        // press tab to move to next focusable field (next line here)
        $(document.activeElement).trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        await testUtils.nextTick();
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_selected_row .o_field_many2one input').get(0));

        list.destroy();
    });

    QUnit.test('edition, then navigation with tab (with a readonly field)', async function (assert) {
        // This test makes sure that if we have 2 cells in a row, the first in
        // edit mode, and the second one readonly, then if we edit and press TAB,
        // (before debounce), the save operation is properly done (before
        // selecting the next row)
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
            mockRPC: function (route, args) {
                if (args.method) {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
            },
            fieldDebounce: 1,
        });

        // click on first td and press TAB
        await testUtils.dom.click(list.$('td:contains(yop)'));
        await testUtils.fields.editSelect(list.$('tr.o_selected_row input[name="foo"]'), 'new value');
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');

        assert.strictEqual(list.$('tbody tr:first td:contains(new value)').length, 1,
            "should have the new value visible in dom");
        assert.verifySteps(["write", "read"]);
        list.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable list with a readonly field [REQUIRE FOCUS]', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="int_field" readonly="1"/>' +
                    '<field name="qux"/>' +
                '</tree>',
        });

        // start on 'qux', line 3
        await testUtils.dom.click(list.$('.o_data_row:nth(2) .o_data_cell:nth(2)'));
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(2) .o_data_cell input[name=qux]')[0]);

        // Press 'shift-Tab' -> should go to first cell (same line)
        $(document.activeElement).trigger({type: 'keydown', which: $.ui.keyCode.TAB, shiftKey: true});
        await testUtils.nextTick();
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(2) .o_data_cell input[name=foo]')[0]);

        list.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable list with a readonly field in first column [REQUIRE FOCUS]', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="int_field" readonly="1"/>' +
                    '<field name="foo"/>' +
                    '<field name="qux"/>' +
                '</tree>',
        });

        // start on 'foo', line 3
        await testUtils.dom.click(list.$('.o_data_row:nth(2) .o_data_cell:nth(1)'));
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(2) .o_data_cell input[name=foo]')[0]);

        // Press 'shift-Tab' -> should go to previous line (last cell)
        $(document.activeElement).trigger({type: 'keydown', which: $.ui.keyCode.TAB, shiftKey: true});
        await testUtils.nextTick();
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(1) .o_data_cell input[name=qux]')[0]);

        list.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable list with a readonly field in last column [REQUIRE FOCUS]', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="int_field"/>' +
                    '<field name="foo"/>' +
                    '<field name="qux" readonly="1"/>' +
                '</tree>',
        });

        // start on 'int_field', line 3
        await testUtils.dom.click(list.$('.o_data_row:nth(2) .o_data_cell:first'));
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(2) .o_data_cell input[name=int_field]')[0]);

        // Press 'shift-Tab' -> should go to previous line ('foo' field)
        $(document.activeElement).trigger({type: 'keydown', which: $.ui.keyCode.TAB, shiftKey: true});
        await testUtils.nextTick();
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');
        assert.strictEqual(document.activeElement, list.$('.o_data_row:nth(1) .o_data_cell input[name=foo]')[0]);

        list.destroy();
    });

    QUnit.test('skip invisible fields when navigating list view with TAB', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="bar" invisible="1"/>' +
                    '<field name="int_field"/>' +
                '</tree>',
            res_id: 1,
        });

        await testUtils.dom.click(list.$('td:contains(gnap)'));
        assert.strictEqual(list.$('input[name="foo"]')[0], document.activeElement,
            "foo should be focused");
        await testUtils.fields.triggerKeydown(list.$('input[name="foo"]'), 'tab');
        assert.strictEqual(list.$('input[name="int_field"]')[0], document.activeElement,
            "int_field should be focused");

        list.destroy();
    });

    QUnit.test('skip buttons when navigating list view with TAB (end)', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<button name="kikou" string="Kikou" type="object"/>' +
                '</tree>',
            res_id: 1,
        });

        await testUtils.dom.click(list.$('tbody tr:eq(2) td:eq(1)'));
        assert.strictEqual(list.$('tbody tr:eq(2) input[name="foo"]')[0], document.activeElement,
            "foo should be focused");
        await testUtils.fields.triggerKeydown(list.$('tbody tr:eq(2) input[name="foo"]'), 'tab');
        assert.strictEqual(list.$('tbody tr:eq(3) input[name="foo"]')[0], document.activeElement,
            "next line should be selected");

        list.destroy();
    });

    QUnit.test('skip buttons when navigating list view with TAB (middle)', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    // Adding a button column makes conversions between column and field position trickier
                    '<button name="kikou" string="Kikou" type="object"/>' +
                    '<field name="foo"/>' +
                    '<button name="kikou" string="Kikou" type="object"/>' +
                    '<field name="int_field"/>' +
                '</tree>',
            res_id: 1,
        });

        await testUtils.dom.click(list.$('tbody tr:eq(2) td:eq(2)'));
        assert.strictEqual(list.$('tbody tr:eq(2) input[name="foo"]')[0], document.activeElement,
            "foo should be focused");
        await testUtils.fields.triggerKeydown(list.$('tbody tr:eq(2) input[name="foo"]'), 'tab');
        assert.strictEqual(list.$('tbody tr:eq(2) input[name="int_field"]')[0], document.activeElement,
            "int_field should be focused");

        list.destroy();
    });

    QUnit.test('navigation: not moving down with keydown', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
        });

        await testUtils.dom.click(list.$('td:contains(yop)'));
        assert.hasClass(list.$('tr.o_data_row:eq(0)'),'o_selected_row',
            "1st row should be selected");
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'down');
        assert.hasClass(list.$('tr.o_data_row:eq(0)'),'o_selected_row',
            "1st row should still be selected");
        list.destroy();
    });

    QUnit.test('navigation: moving right with keydown from text field does not move the focus', async function (assert) {
        assert.expect(6);

        this.data.foo.fields.foo.type = 'text';
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                '</tree>',
        });

        await testUtils.dom.click(list.$('td:contains(yop)'));
        var textarea = list.$('textarea[name="foo"]')[0];
        assert.strictEqual(document.activeElement, textarea,
            "textarea should be focused");
        assert.strictEqual(textarea.selectionStart,  0,
            "textarea selection start should be at the beginning");
        assert.strictEqual(textarea.selectionEnd,  3,
            "textarea selection end should be at the end");
        textarea.selectionStart = 3; // Simulate browser keyboard right behavior (unselect)
        assert.strictEqual(document.activeElement, textarea,
            "textarea should still be focused");
        assert.ok(textarea.selectionStart === 3 && textarea.selectionEnd === 3,
            "textarea value ('yop') should not be selected and cursor should be at the end");
        await testUtils.fields.triggerKeydown($(textarea), 'right');
        assert.strictEqual(document.activeElement, list.$('textarea[name="foo"]')[0],
            "next field (checkbox) should now be focused");
        list.destroy();
    });

    QUnit.test('discarding changes in a row properly updates the rendering', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="top">' +
                    '<field name="foo"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('.o_data_cell:first').text(), "yop",
            "first cell should contain 'yop'");

        await testUtils.dom.click(list.$('.o_data_cell:first'));
        await testUtils.fields.editInput(list.$('input[name="foo"]'), "hello");
        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        assert.strictEqual($('.modal:visible').length, 1,
            "a modal to ask for discard should be visible");

        await testUtils.dom.click($('.modal:visible .btn-primary'));
        assert.strictEqual(list.$('.o_data_cell:first').text(), "yop",
            "first cell should still contain 'yop'");

        list.destroy();
    });

    QUnit.test('numbers in list are right-aligned', async function (assert) {
        assert.expect(2);

        var currencies = {};
        _.each(this.data.res_currency.records, function (currency) {
            currencies[currency.id] = currency;
        });
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="top">' +
                    '<field name="foo"/>' +
                    '<field name="qux"/>' +
                    '<field name="amount" widget="monetary"/>' +
                    '<field name="currency_id" invisible="1"/>' +
                '</tree>',
            session: {
                currencies: currencies,
            },
        });

        var nbCellRight = _.filter(list.$('.o_data_row:first > .o_data_cell'), function (el) {
            var style = window.getComputedStyle(el);
            return style.textAlign === 'right';
        }).length;
        assert.strictEqual(nbCellRight, 2,
            "there should be two right-aligned cells");

        await testUtils.dom.click(list.$('.o_data_cell:first'));

        var nbInputRight = _.filter(list.$('.o_data_row:first > .o_data_cell input'), function (el) {
            var style = window.getComputedStyle(el);
            return style.textAlign === 'right';
        }).length;
        assert.strictEqual(nbInputRight, 2,
            "there should be two right-aligned input");

        list.destroy();
    });

    QUnit.test('field values are escaped', async function (assert) {
        assert.expect(1);
        var value = '<script>throw Error();</script>';

        this.data.foo.records[0].foo = value;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/></tree>',
        });

        assert.strictEqual(list.$('.o_data_cell:first').text(), value,
            "value should have been escaped");

        list.destroy();
    });

    QUnit.test('pressing ESC discard the current line changes', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/></tree>',
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        assert.containsN(list, 'tr.o_data_row', 5,
            "should currently adding a 5th data row");

        await testUtils.fields.triggerKeydown(list.$('input[name="foo"]'), 'escape');
        assert.containsN(list, 'tr.o_data_row', 4,
            "should have only 4 data row after escape");
        assert.containsNone(list, 'tr.o_data_row.o_selected_row',
            "no rows should be selected");
        assert.ok(!list.$buttons.find('.o_list_button_save').is(':visible'),
            "should not have a visible save button");
        list.destroy();
    });

    QUnit.test('pressing ESC discard the current line changes (with required)', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
        });

        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        assert.containsN(list, 'tr.o_data_row', 5,
            "should currently adding a 5th data row");

        await testUtils.fields.triggerKeydown(list.$('input[name="foo"]'), 'escape');
        assert.containsN(list, 'tr.o_data_row', 4,
            "should have only 4 data row after escape");
        assert.containsNone(list, 'tr.o_data_row.o_selected_row',
            "no rows should be selected");
        assert.ok(!list.$buttons.find('.o_list_button_save').is(':visible'),
            "should not have a visible save button");
        list.destroy();
    });

    QUnit.test('field with password attribute', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo" password="True"/></tree>',
        });

        assert.strictEqual(list.$('td.o_data_cell:eq(0)').text(), '***',
            "should display string as password");
        assert.strictEqual(list.$('td.o_data_cell:eq(1)').text(), '****',
            "should display string as password");

        list.destroy();
    });

    QUnit.test('list with handle widget', async function (assert) {
        assert.expect(11);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="amount" widget="float" digits="[5,0]"/>' +
                  '</tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    assert.strictEqual(args.offset, -4,
                        "should write the sequence starting from the lowest current one");
                    assert.strictEqual(args.field, 'int_field',
                        "should write the right field as sequence");
                    assert.deepEqual(args.ids, [4, 2 , 3],
                        "should write the sequence in correct order");
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "default first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '500',
            "default second record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '300',
            "default third record should have amount 300");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '0',
            "default fourth record should have amount 0");

        // Drag and drop the fourth line in second position
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "new first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '0',
            "new second record should have amount 0");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '500',
            "new third record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '300',
            "new fourth record should have amount 300");

        list.destroy();
    });

    QUnit.test('result of consecutive resequences is correctly sorted', async function (assert) {
        assert.expect(9);
        this.data = { // we want the data to be minimal to have a minimal test
            foo: {
                fields: {int_field: {string: "int_field", type: "integer", sortable: true}},
                records: [
                    {id: 1, int_field: 11},
                    {id: 2, int_field: 12},
                    {id: 3, int_field: 13},
                    {id: 4, int_field: 14},
                ]
            }
        };
        var moves = 0;
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="id"/>' +
                  '</tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    if (moves === 0) {
                        assert.deepEqual(args, {
                            model: "foo",
                            ids: [4, 3],
                            offset: 13,
                            field: "int_field",
                        });
                    }
                    if (moves === 1) {
                        assert.deepEqual(args, {
                            model: "foo",
                            ids: [4, 2],
                            offset: 12,
                            field: "int_field",
                        });
                    }
                    if (moves === 2) {
                        assert.deepEqual(args, {
                            model: "foo",
                            ids: [2, 4],
                            offset: 12,
                            field: "int_field",
                        });
                    }
                    if (moves === 3) {
                        assert.deepEqual(args, {
                            model: "foo",
                            ids: [4, 2],
                            offset: 12,
                            field: "int_field",
                        });
                    }
                    moves += 1;
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.strictEqual(list.$('tbody tr td.o_list_number').text(), '1234',
            "default should be sorted by id");
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').eq(2),
            {position: 'top'}
        );
        assert.strictEqual(list.$('tbody tr td.o_list_number').text(), '1243',
            "the int_field (sequence) should have been correctly updated");

        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(2),
            list.$('tbody tr').eq(1),
            {position: 'top'}
        );
        assert.deepEqual(list.$('tbody tr td.o_list_number').text(), '1423',
            "the int_field (sequence) should have been correctly updated");

        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(1),
            list.$('tbody tr').eq(3),
            {position: 'top'}
        );
        assert.deepEqual(list.$('tbody tr td.o_list_number').text(), '1243',
            "the int_field (sequence) should have been correctly updated");

        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(2),
            list.$('tbody tr').eq(1),
            {position: 'top'}
        );
        assert.deepEqual(list.$('tbody tr td.o_list_number').text(), '1423',
            "the int_field (sequence) should have been correctly updated");
        list.destroy();
    });

    QUnit.test('editable list with handle widget', async function (assert) {
        assert.expect(12);

        // resequence makes sense on a sequence field, not on arbitrary fields
        this.data.foo.records[0].int_field = 0;
        this.data.foo.records[1].int_field = 1;
        this.data.foo.records[2].int_field = 2;
        this.data.foo.records[3].int_field = 3;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top" default_order="int_field">' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="amount" widget="float" digits="[5,0]"/>' +
                  '</tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    assert.strictEqual(args.offset, 1,
                        "should write the sequence starting from the lowest current one");
                    assert.strictEqual(args.field, 'int_field',
                        "should write the right field as sequence");
                    assert.deepEqual(args.ids, [4, 2, 3],
                        "should write the sequence in correct order");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "default first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '500',
            "default second record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '300',
            "default third record should have amount 300");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '0',
            "default fourth record should have amount 0");

        // Drag and drop the fourth line in second position
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "new first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '0',
            "new second record should have amount 0");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '500',
            "new third record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '300',
            "new fourth record should have amount 300");

        await testUtils.dom.click(list.$('tbody tr:eq(1) td:last'));

        assert.strictEqual(list.$('tbody tr:eq(1) td:last input').val(), '0',
            "the edited record should be the good one");

        list.destroy();
    });

    QUnit.test('editable list, handle widget locks and unlocks on sort', async function (assert) {
        assert.expect(6);

        // we need another sortable field to lock/unlock the handle
        this.data.foo.fields.amount.sortable = true;
        // resequence makes sense on a sequence field, not on arbitrary fields
        this.data.foo.records[0].int_field = 0;
        this.data.foo.records[1].int_field = 1;
        this.data.foo.records[2].int_field = 2;
        this.data.foo.records[3].int_field = 3;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top" default_order="int_field">' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="amount" widget="float"/>' +
                  '</tree>',
        });

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '1200.00500.00300.000.00',
            "default should be sorted by int_field");

        // Drag and drop the fourth line in second position
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        // Handle should be unlocked at this point
        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '1200.000.00500.00300.00',
            "drag and drop should have succeeded, as the handle is unlocked");

        // Sorting by a field different for int_field should lock the handle
        await testUtils.dom.click(list.$('.o_column_sortable').eq(1));

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '0.00300.00500.001200.00',
            "should have been sorted by amount");

        // Drag and drop the fourth line in second position (not)
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '0.00300.00500.001200.00',
            "drag and drop should have failed as the handle is locked");

        // Sorting by int_field should unlock the handle
        await testUtils.dom.click(list.$('.o_column_sortable').eq(0));

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '1200.000.00500.00300.00',
            "records should be ordered as per the previous resequence");

        // Drag and drop the fourth line in second position
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '1200.00300.000.00500.00',
            "drag and drop should have worked as the handle is unlocked");

        list.destroy();
    });

    QUnit.test('editable list with handle widget with slow network', async function (assert) {
        assert.expect(15);

        // resequence makes sense on a sequence field, not on arbitrary fields
        this.data.foo.records[0].int_field = 0;
        this.data.foo.records[1].int_field = 1;
        this.data.foo.records[2].int_field = 2;
        this.data.foo.records[3].int_field = 3;

        var prom = testUtils.makeTestPromise();

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="amount" widget="float" digits="[5,0]"/>' +
                  '</tree>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    var _super = this._super.bind(this);
                    assert.strictEqual(args.offset, 1,
                        "should write the sequence starting from the lowest current one");
                    assert.strictEqual(args.field, 'int_field',
                        "should write the right field as sequence");
                    assert.deepEqual(args.ids, [4, 2, 3],
                        "should write the sequence in correct order");
                    return prom.then(function () {
                        return _super(route, args);
                    });
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "default first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '500',
            "default second record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '300',
            "default third record should have amount 300");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '0',
            "default fourth record should have amount 0");

        // drag and drop the fourth line in second position
        await testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        // edit moved row before the end of resequence
        await testUtils.dom.click(list.$('tbody tr:eq(3) td:last'));
        await testUtils.nextTick();

        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').length, 0,
            "shouldn't edit the line before resequence");

        prom.resolve();
        await testUtils.nextTick();

        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').length, 1,
            "should edit the line after resequence");

        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').val(), '300',
            "fourth record should have amount 300");

        await testUtils.fields.editInput(list.$('tbody tr:eq(3) td:last input'), 301);
        await testUtils.dom.click(list.$('tbody tr:eq(0) td:last'));

        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '0',
            "second record should have amount 1");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '500',
            "third record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '301',
            "fourth record should have amount 301");

        await testUtils.dom.click(list.$('tbody tr:eq(3) td:last'));
        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').val(), '301',
            "fourth record should have amount 301");

        list.destroy();
    });

    QUnit.test('multiple clicks on Add do not create invalid rows', async function (assert) {
        assert.expect(2);

        this.data.foo.onchanges = {
            m2o: function () {},
        };

        var prom = testUtils.makeTestPromise();
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="m2o" required="1"/></tree>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'onchange') {
                    return prom.then(function () {
                        return result;
                    });
                }
                return result;
            },
        });

        assert.containsN(list, '.o_data_row', 4,
            "should contain 4 records");

        // click on Add twice, and delay the onchange
        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        prom.resolve();
        await testUtils.nextTick();

        assert.containsN(list, '.o_data_row', 5,
            "only one record should have been created");

        list.destroy();
    });

    QUnit.test('reference field rendering', async function (assert) {
        assert.expect(4);

        this.data.foo.records.push({
            id: 5,
            reference: 'res_currency,2',
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="reference"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === 'name_get') {
                    assert.step(args.model);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.verifySteps(['bar', 'res_currency'], "should have done 1 name_get by model in reference values");
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').text(), "Value 1USDEUREUR",
            "should have the display_name of the reference");
        list.destroy();
    });

    QUnit.test('editable list view: contexts are correctly sent', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="foo"/>' +
                    '</tree>',
            mockRPC: function (route, args) {
                var context;
                if (route === '/web/dataset/search_read') {
                    context = args.context;
                } else {
                    context = args.kwargs.context;
                }
                assert.strictEqual(context.active_field, 2, "context should be correct");
                assert.strictEqual(context.someKey, 'some value', "context should be correct");
                return this._super.apply(this, arguments);
            },
            session: {
                user_context: {someKey: 'some value'},
            },
            viewOptions: {
                context: {active_field: 2},
            },
        });

        await testUtils.dom.click(list.$('.o_data_cell:first'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=foo]'), 'abc');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        list.destroy();
    });

    QUnit.test('editable list view: multi edition', async function (assert) {
        assert.expect(19);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                        '<field name="foo"/>' +
                        '<field name="int_field"/>' +
                    '</tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'write') {
                    assert.deepEqual(args.args, [[1, 2], { int_field: 666 }],
                        "should write on multi records");
                } else if (args.method === 'read') {
                    if (args.args[0].length !== 1) {
                        assert.deepEqual(args.args, [[1, 2], ['foo', 'int_field']],
                            "should batch the read");
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.verifySteps(['/web/dataset/search_read']);

        // select two records
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_list_record_selector input'));
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_list_record_selector input'));

        // edit a line witout modifying a field
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));
        assert.hasClass(list.$('.o_data_row:eq(0)'), 'o_selected_row',
            "the first row should be selected");
        await testUtils.dom.click('body');
        assert.containsNone(list, '.o_selected_row', "no row should be selected");

        // create a record and edit its value
        await testUtils.dom.click($('.o_list_button_add'));
        assert.verifySteps(['default_get']);

        await testUtils.fields.editInput(list.$('.o_selected_row .o_field_widget[name=int_field]'), 123);
        assert.containsNone($, '.modal', "the multi edition should not be triggered during creation");

        await testUtils.dom.click($('.o_list_button_save'));
        assert.verifySteps(['create', 'read']);

        // edit a field
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=int_field]'), 666);
        assert.containsOnce($, '.modal', "there should be an opened modal");
        assert.ok($('.modal').text().includes('2 valid'), "the number of records should be correctly displayed");

        await testUtils.dom.click($('.modal .btn-primary'));
        assert.verifySteps(['write', 'read']);
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), "yop666",
            "the first row should be updated");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_data_cell').text(), "blip666",
            "the second row should be updated");

        list.destroy();
    });

    QUnit.test('editable list view: multi edition with readonly modifiers', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="id"/>' +
                        '<field name="foo"/>' +
                        '<field name="int_field" attrs=\'{"readonly": [("id", ">" , 2)]}\'/>' +
                    '</tree>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args, [[1, 2], { int_field: 666 }],
                        "should only write on the valid records");
                }
                return this._super.apply(this, arguments);
            },
        });

        // select all records
        await testUtils.dom.click(list.$('th.o_list_record_selector input'));

        // edit a field
        await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(1)'));
        await testUtils.fields.editInput(list.$('.o_field_widget[name=int_field]'), 666);
        assert.ok($('.modal').text().includes('2 valid'),
            "the number of records should be correctly displayed (only 2 not readonly)");
        assert.ok($('.modal').text().includes('2 invalid'),
            "should display the number of invalid records");

        await testUtils.dom.click($('.modal .btn-primary'));
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_data_cell').text(), "1yop666",
            "the first row should be updated");
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_data_cell').text(), "2blip666",
            "the second row should be updated");

        list.destroy();
    });

    QUnit.test('list grouped by date:month', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="date"/></tree>',
            groupBy: ['date:month'],
        });

        assert.strictEqual(list.$('tbody').text(), "January 2017 (1)Undefined (3)",
            "the group names should be correct");

        list.destroy();
    });

    QUnit.test('grouped list edition with toggle_button widget', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="bar" widget="toggle_button"/></tree>',
            groupBy: ['m2o'],
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[1], {bar: false},
                        "should write the correct value");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.containsOnce(list, '.o_data_row:first .o_toggle_button_success',
            "boolean value of the first record should be true");
        await testUtils.dom.click(list.$('.o_data_row:first .o_icon_button'));
        assert.strictEqual(list.$('.o_data_row:first .text-muted:not(.o_toggle_button_success)').length, 1,
            "boolean button should have been updated");

        list.destroy();
    });

    QUnit.test('grouped list view, indentation for empty group', async function (assert) {
        assert.expect(3);

        this.data.foo.fields.priority = {
            string: "Priority",
            type: "selection",
            selection: [[1, "Low"], [2, "Medium"], [3, "High"]],
            default: 1,
        };
        this.data.foo.records.push({id: 5, foo: "blip", int_field: -7, m2o: 1, priority: 2});
        this.data.foo.records.push({id: 6, foo: "blip", int_field: 5, m2o: 1, priority: 3});

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="id"/></tree>',
            groupBy: ['priority', 'm2o'],
            mockRPC: function (route, args) {
                // Override of the read_group to display the row even if there is no record in it,
                // to mock the behavihour of some fields e.g stage_id on the sale order.
                if (args.method === 'web_read_group' && args.kwargs.groupby[0] === "m2o") {
                    return Promise.resolve({
                        groups: [{
                            id: 8,
                            m2o: [1, "Value 1"],
                            m2o_count: 0
                        }, {
                            id: 2,
                            m2o: [2, "Value 2"],
                            m2o_count: 1
                        }],
                        length: 1,
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        // open the first group
        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.strictEqual(list.$('th.o_group_name').eq(1).children().length, 1,
            "There should be an empty element creating the indentation for the subgroup.");
        assert.hasClass(list.$('th.o_group_name').eq(1).children().eq(0), 'fa',
            "The first element of the row name should have the fa class");
        assert.strictEqual(list.$('th.o_group_name').eq(1).children().eq(0).is('span'), true,
            "The first element of the row name should be a span");
        list.destroy();
    });

    QUnit.test('basic support for widgets', async function (assert) {
        assert.expect(1);

        var MyWidget = Widget.extend({
            init: function (parent, dataPoint) {
                this.data = dataPoint.data;
            },
            start: function () {
                this.$el.text(JSON.stringify(this.data));
            },
        });
        widgetRegistry.add('test', MyWidget);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="int_field"/><widget name="test"/></tree>',
        });

        assert.strictEqual(list.$('.o_widget').first().text(), '{"foo":"yop","int_field":10,"id":1}',
            "widget should have been instantiated");

        list.destroy();
        delete widgetRegistry.map.test;
    });

    QUnit.test('use the limit attribute in arch', async function (assert) {
        assert.expect(3);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree limit="2"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                assert.strictEqual(args.limit, 2,
                    'should use the correct limit value');
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(list.pager.$el.text().trim(), '1-2 / 4',
            "pager should be correct");

        assert.containsN(list, '.o_data_row', 2,
            'should display 2 data rows');
        list.destroy();
    });

    QUnit.test('check if the view destroys all widgets and instances', async function (assert) {
        assert.expect(1);

        var instanceNumber = 0;
        testUtils.mock.patch(mixins.ParentedMixin, {
            init: function () {
                instanceNumber++;
                return this._super.apply(this, arguments);
            },
            destroy: function () {
                if (!this.isDestroyed()) {
                    instanceNumber--;
                }
                return this._super.apply(this, arguments);
            }
        });

        var params = {
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                    '<field name="date"/>' +
                    '<field name="int_field"/>' +
                    '<field name="qux"/>' +
                    '<field name="m2o"/>' +
                    '<field name="o2m"/>' +
                    '<field name="m2m"/>' +
                    '<field name="amount"/>' +
                    '<field name="currency_id"/>' +
                    '<field name="datetime"/>' +
                    '<field name="reference"/>' +
                '</tree>',
        };

        var list = await createView(params);
        list.destroy();

        var initialInstanceNumber = instanceNumber;
        instanceNumber = 0;

        list = await createView(params);

        // call destroy function of controller to ensure that it correctly destroys everything
        list.__destroy();

        // + 1 (parent)
        assert.strictEqual(instanceNumber, initialInstanceNumber + 1,
            "every widget must be destroyed exept the parent");

        list.destroy();

        testUtils.mock.unpatch(mixins.ParentedMixin);
    });

    QUnit.test('concurrent reloads finishing in inverse order', async function (assert) {
        assert.expect(4);

        var blockSearchRead = false;
        var prom = testUtils.makeTestPromise();
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            mockRPC: function (route) {
                var result = this._super.apply(this, arguments);
                if (route === '/web/dataset/search_read' && blockSearchRead) {
                    return prom.then(_.constant(result));
                }
                return result;
            },
        });

        assert.containsN(list, '.o_list_view .o_data_row', 4,
            "list view should contain 4 records");

        // reload with a domain (this request is blocked)
        blockSearchRead = true;
        list.reload({domain: [['foo', '=', 'yop']]});
        await testUtils.nextTick();

        assert.containsN(list, '.o_list_view .o_data_row', 4,
            "list view should still contain 4 records (search_read being blocked)");

        // reload without the domain
        blockSearchRead = false;
        list.reload({domain: []});
        await testUtils.nextTick();

        assert.containsN(list, '.o_list_view .o_data_row', 4,
            "list view should still contain 4 records");

        // unblock the RPC
        prom.resolve();
        await testUtils.nextTick();

        assert.containsN(list, '.o_list_view .o_data_row', 4,
            "list view should still contain 4 records");

        list.destroy();
    });

    QUnit.test('list view on a "noCache" model', async function (assert) {
        assert.expect(9);

        testUtils.mock.patch(BasicModel, {
            noCacheModels: BasicModel.prototype.noCacheModels.concat(['foo']),
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="display_name"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                if (_.contains(['create', 'unlink', 'write'], args.method)) {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                hasSidebar: true,
            },
        });
        core.bus.on('clear_cache', list, assert.step.bind(assert, 'clear_cache'));

        // create a new record
        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        await testUtils.fields.editInput(list.$('.o_selected_row .o_field_widget'), 'some value');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        // edit an existing record
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        await testUtils.fields.editInput(list.$('.o_selected_row .o_field_widget'), 'new value');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        // delete a record
        await testUtils.dom.click(list.$('.o_data_row:first .o_list_record_selector input'));
        await testUtils.dom.click(list.sidebar.$('.o_dropdown_toggler_btn:contains(Action)'));
        await testUtils.dom.click(list.sidebar.$('a:contains(Delete)'));
        await testUtils.dom.click($('.modal-footer .btn-primary'));

        assert.verifySteps([
            'create',
            'clear_cache',
            'write',
            'clear_cache',
            'unlink',
            'clear_cache',
        ]);

        list.destroy();
        testUtils.mock.unpatch(BasicModel);

        assert.verifySteps(['clear_cache']); // triggered by the test environment on destroy
    });

    QUnit.test('list should ask to scroll to top on page changes', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree limit="3">' +
                    '<field name="display_name"/>' +
                '</tree>',
            intercepts: {
                scrollTo: function (ev) {
                    assert.strictEqual(ev.data.top, 0,
                        "should ask to scroll to top");
                    assert.step('scroll');
                },
            },
        });

        // switch pages (should ask to scroll)
        await testUtils.dom.click(list.pager.$('.o_pager_next'));
        await testUtils.dom.click(list.pager.$('.o_pager_previous'));
        assert.verifySteps(['scroll', 'scroll'],
            "should ask to scroll when switching pages");

        // change the limit (should not ask to scroll)
        await testUtils.dom.click(list.pager.$('.o_pager_value'));
        await testUtils.fields.editAndTrigger(list.pager.$('.o_pager_value input'),
            '1-2', ['blur']);
        assert.strictEqual(list.pager.$('.o_pager_value').text(), '1-2',
            "should have changed the limit");

        assert.verifySteps([], "should not ask to scroll when changing the limit");

        // switch pages again (should still ask to scroll)
        await testUtils.dom.click(list.pager.$('.o_pager_next'));

        assert.verifySteps(['scroll'], "this is still working after a limit change");

        list.destroy();
    });

    QUnit.test('list with handle field, override default_get, bottom when inline', async function (assert) {
        assert.expect(2);

        this.data.foo.fields.int_field.default = 10;

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="bottom" default_order="int_field">'
                    + '<field name="int_field" widget="handle"/>'
                    + '<field name="foo"/>'
                +'</tree>',
        });

        // starting condition
        assert.strictEqual($('.o_data_cell').text(), "blipblipyopgnap");

        // click add a new line
        // save the record
        // check line is at the correct place

        var inputText = 'ninja';
        await testUtils.dom.click($('.o_list_button_add'));
        await testUtils.fields.editInput(list.$('.o_input[name="foo"]'), inputText);
        await testUtils.dom.click($('.o_list_button_save'));
        await testUtils.dom.click($('.o_list_button_add'));

        assert.strictEqual($('.o_data_cell').text(), "blipblipyopgnap" + inputText);

        list.destroy();
    });

    QUnit.test('create record on list with modifiers depending on id', async function (assert) {
        assert.expect(8);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="id" invisible="1"/>' +
                    '<field name="foo" attrs="{\'readonly\': [[\'id\',\'!=\',False]]}"/>' +
                    '<field name="int_field" attrs="{\'invisible\': [[\'id\',\'!=\',False]]}"/>' +
                '</tree>',
        });

        // add a new record
        await testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        // modifiers should be evaluted to false
        assert.containsOnce(list, '.o_selected_row');
        assert.doesNotHaveClass(list.$('.o_selected_row .o_data_cell:first'), 'o_readonly_modifier');
        assert.doesNotHaveClass(list.$('.o_selected_row .o_data_cell:nth(1)'), 'o_invisible_modifier');

        // set a value and save
        await testUtils.fields.editInput(list.$('.o_selected_row input[name=foo]'), 'some value');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        // modifiers should be evaluted to true
        assert.hasClass(list.$('.o_data_row:first .o_data_cell:first'), 'o_readonly_modifier');
        assert.hasClass(list.$('.o_data_row:first .o_data_cell:nth(1)'), 'o_invisible_modifier');

        // edit again the just created record
        await testUtils.dom.click(list.$('.o_data_row:first .o_data_cell:first'));

        // modifiers should be evaluted to true
        assert.containsOnce(list, '.o_selected_row');
        assert.hasClass(list.$('.o_selected_row .o_data_cell:first'), 'o_readonly_modifier');
        assert.hasClass(list.$('.o_selected_row .o_data_cell:nth(1)'), 'o_invisible_modifier');

        list.destroy();
    });

    QUnit.test('readonly boolean in editable list is readonly', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                      '<field name="foo"/>' +
                      '<field name="bar" attrs="{\'readonly\': [(\'foo\', \'!=\', \'yop\')]}"/>' +
                  '</tree>',
        });

        // clicking on disabled checkbox with active row does not work
        var $disabledCell = list.$('.o_data_row:eq(1) .o_data_cell:last-child');
        await testUtils.dom.click($disabledCell.prev());
        assert.containsOnce($disabledCell, ':disabled:checked');
        var $disabledLabel = $disabledCell.find('.custom-control-label');
        await testUtils.dom.click($disabledLabel);
        assert.containsOnce($disabledCell, ':checked',
            "clicking disabled checkbox did not work"
        );
        assert.ok(
            $(document.activeElement).is('input[type="text"]'),
            "disabled checkbox is not focused after click"
        );

        // clicking on enabled checkbox with active row toggles check mark
        var $enabledCell = list.$('.o_data_row:eq(0) .o_data_cell:last-child');
        await testUtils.dom.click($enabledCell.prev());
        assert.containsOnce($enabledCell, ':checked:not(:disabled)');
        var $enabledLabel = $enabledCell.find('.custom-control-label');
        await testUtils.dom.click($enabledLabel);
        assert.containsNone($enabledCell, ':checked',
            "clicking enabled checkbox worked and unchecked it"
        );
        assert.ok(
            $(document.activeElement).is('input[type="checkbox"]'),
            "enabled checkbox is focused after click"
        );

        list.destroy();
    });

    QUnit.test('grouped list with async widget', async function (assert) {
        assert.expect(4);

        var prom = testUtils.makeTestPromise();
        var AsyncWidget = Widget.extend({
            willStart: function () {
                return prom;
            },
            start: function () {
                this.$el.text('ready');
            },
        });
        widgetRegistry.add('asyncWidget', AsyncWidget);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><widget name="asyncWidget"/></tree>',
            groupBy: ['int_field'],
        });

        assert.containsNone(list, '.o_data_row', "no group should be open");

        await testUtils.dom.click(list.$('.o_group_header:first'));

        assert.containsNone(list, '.o_data_row',
            "should wait for async widgets before opening the group");

        prom.resolve();
        await testUtils.nextTick();

        assert.containsN(list, '.o_data_row', 1, "group should be open");
        assert.strictEqual(list.$('.o_data_row .o_data_cell').text(), 'ready',
            "async widget should be correctly displayed");

        list.destroy();
        delete widgetRegistry.map.asyncWidget;
    });

    QUnit.test('grouped lists with groups_limit attribute', async function (assert) {
        assert.expect(8);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree groups_limit="3"><field name="foo"/></tree>',
            groupBy: ['int_field'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(list, '.o_group_header', 3); // page 1
        assert.containsNone(list, '.o_data_row');
        assert.containsOnce(list, '.o_pager_counter'); // has a pager

        await testUtils.dom.click(list.$('.o_pager_next')); // switch to page 2

        assert.containsN(list, '.o_group_header', 1); // page 2
        assert.containsNone(list, '.o_data_row');

        assert.verifySteps([
            'web_read_group', // read_group page 1
            'web_read_group', // read_group page 2
        ]);

        list.destroy();
    });

    QUnit.test('grouped list with expand attribute', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree expand="1"><field name="foo"/></tree>',
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            }
        });

        assert.containsN(list, '.o_group_header', 2);
        assert.containsN(list, '.o_data_row', 4);
        assert.strictEqual(list.$('.o_data_cell').text(), 'yopblipgnapblip');

        assert.verifySteps([
            'web_read_group', // records are fetched alongside groups
        ]);

        list.destroy();
    });

    QUnit.test('grouped list (two levels) with expand attribute', async function (assert) {
        // the expand attribute only opens the first level groups
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree expand="1"><field name="foo"/></tree>',
            groupBy: ['bar', 'int_field'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            }
        });

        assert.containsN(list, '.o_group_header', 6);

        assert.verifySteps([
            'web_read_group', // global
            'web_read_group', // first group
            'web_read_group', // second group
        ]);

        list.destroy();
    });

    QUnit.test('grouped lists with expand attribute and a lot of groups', async function (assert) {
        assert.expect(8);

        for (var i = 0; i < 15; i++) {
            this.data.foo.records.push({foo: 'record ' + i, int_field: i});
        }

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree expand="1"><field name="foo"/></tree>',
            groupBy: ['int_field'],
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(list, '.o_group_header', 10); // page 1
        assert.containsN(list, '.o_data_row', 11); // one group contains two records
        assert.containsOnce(list, '.o_pager_counter'); // has a pager

        await testUtils.dom.click(list.$('.o_pager_next')); // switch to page 2

        assert.containsN(list, '.o_group_header', 7); // page 2
        assert.containsN(list, '.o_data_row', 7);

        assert.verifySteps([
            'web_read_group', // read_group page 1
            'web_read_group', // read_group page 2
        ]);

        list.destroy();
    });

    QUnit.test('editable grouped lists', async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group

        // enter edition (grouped case)
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        assert.containsOnce(list, '.o_selected_row .o_data_cell:first');

        // click on the body should leave the edition
        await testUtils.dom.click($('body'));
        assert.containsNone(list, '.o_selected_row');

        // reload without groupBy
        await list.reload({groupBy: []});

        // enter edition (ungrouped case)
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        assert.containsOnce(list, '.o_selected_row .o_data_cell:first');

        // click on the body should leave the edition
        await testUtils.dom.click($('body'));
        assert.containsNone(list, '.o_selected_row');

        list.destroy();
    });

    QUnit.test('grouped lists are editable (ungrouped first)', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
        });

        // enter edition (ungrouped case)
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        assert.containsOnce(list, '.o_selected_row .o_data_cell:first');

        // reload with groupBy
        await list.reload({groupBy: ['bar']});

        // open first group
        await testUtils.dom.click(list.$('.o_group_header:first'));

        // enter edition (grouped case)
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        assert.containsOnce(list, '.o_selected_row .o_data_cell:first');

        list.destroy();
    });

    QUnit.test('char field edition in editable grouped list', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        await testUtils.dom.click(list.$('.o_data_cell:first'));
        await testUtils.fields.editAndTrigger(list.$('tr.o_selected_row .o_data_cell:first input[name="foo"]'), 'pla', 'input');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        assert.strictEqual(this.data.foo.records[0].foo, 'pla',
            "the edition should have been properly saved");
        assert.containsOnce(list, '.o_data_row:first:contains(pla)');

        list.destroy();
    });

    QUnit.test('control panel buttons in editable grouped list views', async function (assert) {
        assert.expect(2);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
        });

        assert.isNotVisible(list.$buttons.find('.o_list_button_add'));

        // reload without groupBy
        await list.reload({groupBy: []});
        assert.isVisible(list.$buttons.find('.o_list_button_add'));

        list.destroy();
    });

    QUnit.test('edit a line and discard it in grouped editable', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="int_field"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first'));
        await testUtils.dom.click(list.$('.o_data_row:nth(2) > td:contains(gnap)'));
        assert.ok(list.$('.o_data_row:nth(2)').is('.o_selected_row'),
            "third group row should be in edition");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        await testUtils.dom.click(list.$('.o_data_row:nth(0) > td:contains(yop)'));
        assert.ok(list.$('.o_data_row:eq(0)').is('.o_selected_row'),
            "first group row should be in edition");

        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        assert.containsNone(list, '.o_selected_row');

        await testUtils.dom.click(list.$('.o_data_row:nth(2) > td:contains(gnap)'));
        assert.containsOnce(list, '.o_selected_row');
        assert.ok(list.$('.o_data_row:nth(2)').is('.o_selected_row'),
            "third group row should be in edition");

        list.destroy();
    });

    QUnit.test('add and discard a record in a multi-level grouped list view', async function (assert) {
        assert.expect(7);

        testUtils.mock.patch(basicFields.FieldChar, {
            destroy: function () {
                assert.step('destroy');
                this._super.apply(this, arguments);
            },
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
            groupBy: ['foo', 'bar'],
        });

        // unfold first subgroup
        await testUtils.dom.click(list.$('.o_group_header:first'));
        await testUtils.dom.click(list.$('.o_group_header:eq(1)'));
        assert.hasClass(list.$('.o_group_header:first'), 'o_group_open');
        assert.hasClass(list.$('.o_group_header:eq(1)'), 'o_group_open');
        assert.containsOnce(list, '.o_data_row');

        // add a record to first subgroup
        await testUtils.dom.click(list.$('.o_group_field_row_add a'));
        assert.containsN(list, '.o_data_row', 2);

        // discard
        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        assert.containsOnce(list, '.o_data_row');

        assert.verifySteps(['destroy']);

        testUtils.mock.unpatch(basicFields.FieldChar);
        list.destroy();
    });

    QUnit.test('inputs are disabled when unselecting rows in grouped editable', async function (assert) {
        assert.expect(1);

        var $input;
        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.strictEqual($input.prop('disabled'), true,
                        "input should be disabled");
                }
                return this._super.apply(this, arguments);
            },
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first'));
        await testUtils.dom.click(list.$('td:contains(yop)'));
        $input = list.$('tr.o_selected_row input[name="foo"]');
        await testUtils.fields.editAndTrigger($input, 'lemon', 'input');
        await testUtils.fields.triggerKeydown($input, 'tab');

        list.destroy();
    });

    QUnit.test('pressing ESC in editable grouped list should discard the current line changes', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        assert.containsN(list, 'tr.o_data_row', 3);

        await testUtils.dom.click(list.$('.o_data_cell:first'));

        // update name by "foo"
        await testUtils.fields.editAndTrigger(list.$('tr.o_selected_row .o_data_cell:first input[name="foo"]'), 'new_value', 'input');
        // discard by pressing ESC
        await testUtils.fields.triggerKeydown(list.$('input[name="foo"]'), 'escape');
        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));

        assert.containsOnce(list, 'tbody tr td:contains(yop)');
        assert.containsN(list, 'tr.o_data_row', 3);
        assert.containsNone(list, 'tr.o_data_row.o_selected_row');
        assert.isNotVisible(list.$buttons.find('.o_list_button_save'));

        list.destroy();
    });

    QUnit.test('pressing TAB in editable="bottom" grouped list', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            groupBy: ['bar'],
        });

        // open two groups
        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:nth(1)'));
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        await testUtils.dom.click(list.$('.o_data_cell:first'));
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');

        // Press 'Tab' -> should go to first line of next group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(3)'), 'o_selected_row');

        // Press 'Tab' -> should go back to first line of first group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');

        list.destroy();
    });

    QUnit.test('pressing TAB in editable="top" grouped list', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/></tree>',
            groupBy: ['bar'],
        });

        // open two groups
        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:nth(1)'));
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        await testUtils.dom.click(list.$('.o_data_cell:first'));

        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');

        // Press 'Tab' -> should go to first line of next group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(3)'), 'o_selected_row');

        // Press 'Tab' -> should go back to first line of first group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');

        list.destroy();
    });

    QUnit.test('pressing TAB in editable grouped list with create=0', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom" create="0"><field name="foo"/></tree>',
            groupBy: ['bar'],
        });

        // open two groups
        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:nth(1)'));
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        await testUtils.dom.click(list.$('.o_data_cell:first'));

        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(1)'), 'o_selected_row');

        // Press 'Tab' -> should go to next line (still in first group)
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');

        // Press 'Tab' -> should go to first line of next group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:nth(3)'), 'o_selected_row');

        // Press 'Tab' -> should go back to first line of first group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.hasClass(list.$('.o_data_row:first'), 'o_selected_row');

        list.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable="bottom" grouped list', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        // navigate inside a group
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_data_cell')); // select second row of first group
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press Shft+tab
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('tr.o_data_row:first'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // navigate between groups
        await testUtils.dom.click(list.$('.o_data_cell:eq(3)')); // select row of second group

        // press Shft+tab
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');

        list.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable="top" grouped list', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        // navigate inside a group
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_data_cell')); // select second row of first group
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press Shft+tab
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('tr.o_data_row:first'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // navigate between groups
        await testUtils.dom.click(list.$('.o_data_cell:eq(3)')); // select row of second group

        // press Shft+tab
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');

        list.destroy();
    });

    QUnit.test('pressing SHIFT-TAB in editable grouped list with create="0"', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top" create="0"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        // navigate inside a group
        await testUtils.dom.click(list.$('.o_data_row:eq(1) .o_data_cell')); // select second row of first group
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press Shft+tab
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('tr.o_data_row:first'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // navigate between groups
        await testUtils.dom.click(list.$('.o_data_cell:eq(3)')); // select row of second group

        // press Shft+tab
        list.$('tr.o_selected_row input').trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        await testUtils.nextTick();
        assert.hasClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');

        list.destroy();
    });

    QUnit.test('editing then pressing TAB in editable grouped list', async function (assert) {
        assert.expect(19);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            groupBy: ['bar'],
        });

        // open two groups
        await testUtils.dom.click(list.$('.o_group_header:first'));
        assert.containsN(list, '.o_data_row', 3, 'first group contains 3 rows');
        await testUtils.dom.click(list.$('.o_group_header:nth(1)'));
        assert.containsN(list, '.o_data_row', 4, 'first group contains 1 row');

        // select and edit last row of first group
        await testUtils.dom.click(list.$('.o_data_row:nth(2) .o_data_cell'));
        assert.hasClass(list.$('.o_data_row:nth(2)'), 'o_selected_row');
        await testUtils.fields.editInput(list.$('.o_selected_row input[name="foo"]'), 'new value');

        // Press 'Tab' -> should create a new record as we edited the previous one
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.containsN(list, '.o_data_row', 5);
        assert.hasClass(list.$('.o_data_row:nth(3)'), 'o_selected_row');

        // fill foo field for the new record and press 'tab' -> should create another record
        await testUtils.fields.editInput(list.$('.o_selected_row input[name="foo"]'), 'new record');
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');

        assert.containsN(list, '.o_data_row', 6);
        assert.hasClass(list.$('.o_data_row:nth(4)'), 'o_selected_row');

        // leave this new row empty and press tab -> should discard the new record and move to the
        // next group
        await testUtils.fields.triggerKeydown(list.$('.o_selected_row input'), 'tab');
        assert.containsN(list, '.o_data_row', 5);
        assert.hasClass(list.$('.o_data_row:nth(4)'), 'o_selected_row');

        assert.verifySteps([
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            'write',
            'read',
            'default_get',
            'create',
            'read',
            'default_get',
        ]);

        list.destroy();
    });

    QUnit.test('editing then pressing TAB (with a readonly field) in grouped list', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            groupBy: ['bar'],
            fieldDebounce: 1
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        // click on first td and press TAB
        await testUtils.dom.click(list.$('td:contains(yop)'));
        await testUtils.fields.editAndTrigger(list.$('tr.o_selected_row input[name="foo"]'), 'new value', 'input');
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input[name="foo"]'), 'tab');

        assert.containsOnce(list, 'tbody tr td:contains(new value)');
        assert.verifySteps([
            'web_read_group',
            '/web/dataset/search_read',
            'write',
            'read',
        ]);

        list.destroy();
    });

    QUnit.test('pressing ENTER in editable="bottom" grouped list view', async function (assert) {
        assert.expect(11);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        await testUtils.dom.click(list.$('.o_group_header:nth(1)')); // open second group
        assert.containsN(list, 'tr.o_data_row', 4);
        await testUtils.dom.click(list.$('.o_data_row:nth(1) .o_data_cell')); // click on second line
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press enter in input should move to next record
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input'), 'enter');

        assert.hasClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press enter on last row should create a new record
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input'), 'enter');

        assert.containsN(list, 'tr.o_data_row', 5);
        assert.hasClass(list.$('tr.o_data_row:eq(3)'), 'o_selected_row');

        assert.verifySteps([
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            'default_get',
        ]);

        list.destroy();
    });

    QUnit.test('pressing ENTER in editable="top" grouped list view', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        await testUtils.dom.click(list.$('.o_group_header:nth(1)')); // open second group
        assert.containsN(list, 'tr.o_data_row', 4);
        await testUtils.dom.click(list.$('.o_data_row:nth(1) .o_data_cell')); // click on second line
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press enter in input should move to next record
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input'), 'enter');

        assert.hasClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press enter on last row should move to first record of next group
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input'), 'enter');

        assert.hasClass(list.$('tr.o_data_row:eq(3)'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');

        assert.verifySteps([
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
        ]);

        list.destroy();
    });

    QUnit.test('pressing ENTER in editable grouped list view with create=0', async function (assert) {
        assert.expect(10);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom" create="0"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        await testUtils.dom.click(list.$('.o_group_header:nth(1)')); // open second group
        assert.containsN(list, 'tr.o_data_row', 4);
        await testUtils.dom.click(list.$('.o_data_row:nth(1) .o_data_cell')); // click on second line
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press enter in input should move to next record
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input'), 'enter');

        assert.hasClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row');

        // press enter on last row should move to first record of next group
        await testUtils.fields.triggerKeydown(list.$('tr.o_selected_row input'), 'enter');

        assert.hasClass(list.$('tr.o_data_row:eq(3)'), 'o_selected_row');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row');

        assert.verifySteps([
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
        ]);

        list.destroy();
    });

    QUnit.test('cell-level keyboard navigation in non-editable list', async function (assert) {
        assert.expect(16);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo" required="1"/></tree>',
            intercepts: {
                switch_view: function (event) {
                    assert.strictEqual(event.data.res_id, 3,
                        "'switch_view' event has been triggered");
                },
            },
        });

        assert.ok(document.activeElement.classList.contains('o_searchview_input'), 'default focus should be in search view');
        // switch focus to the create button in tests while it works on live
        $('.o_list_button_add').focus();
        assert.ok(document.activeElement.classList.contains('o_list_button_add'),
            'focus should now be in create button');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'focus should now be on the record selector');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'focus should now be in first row input');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.tagName, 'TD',
            'focus should now be in field TD');
        assert.strictEqual(document.activeElement.textContent, 'yop',
            'focus should now be in first row field');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.textContent, 'yop',
            'should not cycle at end of line');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'focus should now be in second row field');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'gnap',
            'focus should now be in third row field');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'focus should now be in last row field');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'focus should still be in last row field (arrows do not cycle)');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'focus should still be in last row field (arrows still do not cycle)');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'focus should now be in last row input');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'should not cycle at start of line');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.textContent, 'gnap',
            'focus should now be in third row field');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        list.destroy();
    });

    QUnit.test('cell-level keyboard navigation in editable grouped list', async function (assert) {
        assert.expect(56);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open first group
        await testUtils.dom.click(list.$('td:contains(blip)')); // select row of first group
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row',
            'second row should be opened');

        var $secondRowInput = list.$('tr.o_data_row:eq(1) td:eq(1) input');
        assert.strictEqual($secondRowInput.val(), 'blip',
            'second record should be in edit mode');

        await testUtils.fields.editAndTrigger($secondRowInput, 'blipbloup', 'input');
        assert.strictEqual($secondRowInput.val(), 'blipbloup',
            'second record should be changed but not saved yet');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'escape');

        assert.hasClass($('body'), 'modal-open',
            'record has been modified, are you sure modal should be opened');
        await testUtils.dom.click($('body .modal button span:contains(Ok)'));

        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row',
            'second row should be closed');
        assert.strictEqual(document.activeElement.tagName, 'TD',
            'focus is in field td');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'second field of second record should be focused');
        assert.strictEqual(list.$('tr.o_data_row:eq(1) td:eq(1)').text(), 'blip',
            'change should not have been saved');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'record selector should be focused');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.tagName, 'TD',
            'focus is in first record td');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        var $firstRowInput = list.$('tr.o_data_row:eq(0) td:eq(1) input');
        assert.hasClass(list.$('tr.o_data_row:eq(0)'), 'o_selected_row',
            'first row should be selected');
        assert.strictEqual($firstRowInput.val(), 'yop',
            'first record should be in edit mode');

        await testUtils.fields.editAndTrigger($firstRowInput, 'Zipadeedoodah', 'input');
        assert.strictEqual($firstRowInput.val(), 'Zipadeedoodah',
            'first record should be changed but not saved yet');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.strictEqual(list.$('tr.o_data_row:eq(0) td:eq(1)').text(), 'Zipadeedoodah',
            'first record should be saved');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(0)'), 'o_selected_row',
            'first row should be closed');
        assert.hasClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row',
            'second row should be opened');
        assert.strictEqual(list.$('tr.o_data_row:eq(1) td:eq(1) input').val(), 'blip',
            'second record should be in edit mode');

        assert.strictEqual(document.activeElement.value, 'blip',
            'second record input should be focused');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.value, 'blip',
            'second record input should still be focused (arrows movements are disabled in edit)');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(document.activeElement.value, 'blip',
            'second record input should still be focused (arrows movements are still disabled in edit)');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'escape');
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(1)'), 'o_selected_row',
            'second row should be closed');
        assert.strictEqual(document.activeElement.tagName, 'TD',
            'focus is in field td');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'second field of second record should be focused');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');

        assert.strictEqual(document.activeElement.tagName, 'A',
            'should focus the "Add a line" button');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');

        assert.strictEqual(document.activeElement.textContent, 'false (1)',
            'focus should be on second group header');
        assert.strictEqual(list.$('tr.o_data_row').length, 3,
            'should have 3 rows displayed');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.strictEqual(list.$('tr.o_data_row').length, 4,
            'should have 4 rows displayed');
        assert.strictEqual(document.activeElement.textContent, 'false (1)',
            'focus should still be on second group header');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'second field of last record should be focused');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'A',
            'should focus the "Add a line" button');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'A',
            'arrow navigation should not cycle (focus still on last row)');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        await testUtils.fields.editAndTrigger($('tr.o_data_row:eq(4) td:eq(1) input'),
            'cheateur arrete de cheater', 'input');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.strictEqual(list.$('tr.o_data_row').length, 6,
            'should have 6 rows displayed (new record + new edit line)');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'escape');
        assert.strictEqual(document.activeElement.tagName, 'A',
            'should focus the "Add a line" button');

        // come back to the top
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');

        assert.strictEqual(document.activeElement.tagName, 'TH',
            'focus is in table header');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'focus is in header input');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(document.activeElement.tagName, 'TD',
            'focus is in field td');
        assert.strictEqual(document.activeElement.textContent, 'Zipadeedoodah',
            'second field of first record should be focused');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        assert.strictEqual(document.activeElement.textContent, 'true (3)',
            'focus should be on first group header');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.strictEqual(list.$('tr.o_data_row').length, 2,
            'should have 2 rows displayed (first group should be closed)');
        assert.strictEqual(document.activeElement.textContent, 'true (3)',
            'focus should still be on first group header');

        assert.strictEqual(list.$('tr.o_data_row').length, 2,
            'should have 2 rows displayed');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(list.$('tr.o_data_row').length, 5,
            'should have 5 rows displayed');
        assert.strictEqual(document.activeElement.textContent, 'true (3)',
            'focus is still in header');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'right');
        assert.strictEqual(list.$('tr.o_data_row').length, 5,
            'should have 5 rows displayed');
        assert.strictEqual(document.activeElement.textContent, 'true (3)',
            'focus is still in header');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(list.$('tr.o_data_row').length, 2,
            'should have 2 rows displayed');
        assert.strictEqual(document.activeElement.textContent, 'true (3)',
            'focus is still in header');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'left');
        assert.strictEqual(list.$('tr.o_data_row').length, 2,
            'should have 2 rows displayed');
        assert.strictEqual(document.activeElement.textContent, 'true (3)',
            'focus is still in header');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'false (2)',
            'focus should now be on second group header');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'TD',
            'record td should be focused');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'second field of first record of second group should be focused');

        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'cheateur arrete de cheater',
            'second field of last record of second group should be focused');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'A',
            'should focus the "Add a line" button');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        assert.strictEqual(document.activeElement.textContent, 'cheateur arrete de cheater',
        'second field of last record of second group should be focused (special case: the first td of the "Add a line" line was skipped');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        assert.strictEqual(document.activeElement.textContent, 'blip',
            'second field of first record of second group should be focused');

        list.destroy();
    });

    QUnit.test('execute group header button with keyboard navigation', async function (assert) {
        assert.expect(13);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<groupby name="m2o">' +
                        '<button type="object" name="some_method" string="Do this"/>' +
                    '</groupby>' +
                '</tree>',
            groupBy: ['m2o'],
            intercepts: {
                execute_action: function (ev) {
                    assert.strictEqual(ev.data.action_data.name, 'some_method');
                },
            },
        });

        assert.containsNone(list, '.o_data_row', "all groups should be closed");

        // focus create button as a starting point
        list.$('.o_list_button_add').focus();
        assert.ok(document.activeElement.classList.contains('o_list_button_add'));
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'focus should now be on the record selector (list header)');
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.textContent, 'Value 1 (3)',
            'focus should be on first group header');

        // unfold first group
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.containsN(list, '.o_data_row', 3, "first group should be open");

        // move to first record of opened group
        await testUtils.fields.triggerKeydown($(document.activeElement), 'down');
        assert.strictEqual(document.activeElement.tagName, 'INPUT',
            'focus should be in first row checkbox');

        // move back to the group header
        await testUtils.fields.triggerKeydown($(document.activeElement), 'up');
        assert.ok(document.activeElement.classList.contains('o_group_name'),
            'focus should be back on first group header');

        // fold the group
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.ok(document.activeElement.classList.contains('o_group_name'),
            'focus should still be on first group header');
        assert.containsNone(list, '.o_data_row', "first group should now be folded");

        // unfold the group
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.ok(document.activeElement.classList.contains('o_group_name'),
            'focus should still be on first group header');
        assert.containsN(list, '.o_data_row', 3, "first group should be open");

        // simulate a move to the group header button with tab (we can't trigger a native event
        // programmatically, see https://stackoverflow.com/a/32429197)
        list.$('.o_group_header .o_group_buttons button:first').focus();
        assert.strictEqual(document.activeElement.tagName, 'BUTTON',
            'focus should be on the group header button');

        // click on the button by pressing enter
        await testUtils.fields.triggerKeydown($(document.activeElement), 'enter');
        assert.containsN(list, '.o_data_row', 3, "first group should still be open");

        list.destroy();
    });

    QUnit.test('add a new row in grouped editable="top" list', async function (assert) {
        assert.expect(7);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open group
        await testUtils.dom.click(list.$('.o_group_field_row_add a'));// add a new row
        assert.strictEqual(list.$('.o_selected_row .o_input[name=foo]')[0], document.activeElement,
            'The first input of the line should have the focus');
        assert.containsN(list, 'tbody:nth(1) .o_data_row', 4);

        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard')); // discard new row
        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        assert.containsOnce(list, 'tbody:nth(3) .o_data_row');

        await testUtils.dom.click(list.$('.o_group_field_row_add a:eq(1)')); // create row in second group
        assert.strictEqual(list.$('.o_group_name:eq(1)').text(), 'false (2)',
            "group should have correct name and count");
        assert.containsN(list, 'tbody:nth(3) .o_data_row', 2);
        assert.hasClass(list.$('.o_data_row:nth(3)'), 'o_selected_row');

        await testUtils.fields.editAndTrigger(list.$('tr.o_selected_row input[name="foo"]'), 'pla', 'input');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.containsN(list, 'tbody:nth(3) .o_data_row', 2);

        list.destroy();
    });

    QUnit.test('add a new row in grouped editable="bottom" list', async function (assert) {
        assert.expect(5);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open group
        await testUtils.dom.click(list.$('.o_group_field_row_add a'));// add a new row
        assert.hasClass(list.$('.o_data_row:nth(3)'), 'o_selected_row');
        assert.containsN(list, 'tbody:nth(1) .o_data_row', 4);

        await testUtils.dom.click(list.$buttons.find('.o_list_button_discard')); // discard new row
        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        assert.containsOnce(list, 'tbody:nth(3) .o_data_row');
        await testUtils.dom.click(list.$('.o_group_field_row_add a:eq(1)')); // create row in second group
        assert.hasClass(list.$('.o_data_row:nth(4)'), 'o_selected_row');

        await testUtils.fields.editAndTrigger(list.$('tr.o_selected_row input[name="foo"]'), 'pla', 'input');
        await testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.containsN(list, 'tbody:nth(3) .o_data_row', 2);

        list.destroy();
    });

    QUnit.test('editable grouped list with create="0"', async function (assert) {
        assert.expect(1);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top" create="0"><field name="foo" required="1"/></tree>',
            groupBy: ['bar'],
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open group
        assert.containsNone(list, '.o_group_field_row_add a',
            "Add a line should not be available in readonly");

        list.destroy();
    });

    QUnit.test('add a new row in (selection) grouped editable list', async function (assert) {
        assert.expect(6);

        this.data.foo.fields.priority = {
            string: "Priority",
            type: "selection",
            selection: [[1, "Low"], [2, "Medium"], [3, "High"]],
            default: 1,
        };
        this.data.foo.records.push({id: 5, foo: "blip", int_field: -7, m2o: 1, priority: 2});
        this.data.foo.records.push({id: 6, foo: "blip", int_field: 5, m2o: 1, priority: 3});

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="foo"/>' +
                        '<field name="priority"/>' +
                        '<field name="m2o"/>' +
                    '</tree>',
            groupBy: ['priority'],
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    assert.step(args.kwargs.context.default_priority.toString());
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$('.o_group_header:first')); // open group
        await testUtils.dom.click(list.$('.o_group_field_row_add a')); // add a new row
        await testUtils.dom.click($('body')); // unselect row
        assert.verifySteps(['1']);
        assert.strictEqual(list.$('.o_data_row .o_data_cell:eq(1)').text(), 'Low',
            "should have a column name with a value from the groupby");

        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        await testUtils.dom.click(list.$('.o_group_field_row_add a:eq(1)')); // create row in second group
        await testUtils.dom.click($('body')); // unselect row
        assert.strictEqual(list.$('.o_data_row:nth(5) .o_data_cell:eq(1)').text(), 'Medium',
            "should have a column name with a value from the groupby");
        assert.verifySteps(['2']);

        list.destroy();
    });

    QUnit.test('add a new row in (m2o) grouped editable list', async function (assert) {
        assert.expect(6);

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                        '<field name="foo"/>' +
                        '<field name="m2o"/>' +
                    '</tree>',
            groupBy: ['m2o'],
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    assert.step(args.kwargs.context.default_m2o.toString());
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(list.$('.o_group_header:first'));
        await testUtils.dom.click(list.$('.o_group_field_row_add a'));
        await testUtils.dom.click($('body')); // unselect row
        assert.strictEqual(list.$('tbody:eq(1) .o_data_row:first .o_data_cell:eq(1)').text(), 'Value 1',
            "should have a column name with a value from the groupby");
        assert.verifySteps(['1']);

        await testUtils.dom.click(list.$('.o_group_header:eq(1)')); // open second group
        await testUtils.dom.click(list.$('.o_group_field_row_add a:eq(1)')); // create row in second group
        await testUtils.dom.click($('body')); // unselect row
        assert.strictEqual(list.$('tbody:eq(3) .o_data_row:first .o_data_cell:eq(1)').text(), 'Value 2',
            "should have a column name with a value from the groupby");
        assert.verifySteps(['2']);

        list.destroy();
    });

    QUnit.test('list view with optional fields rendering', async function (assert) {
        assert.expect(9);

        var RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="m2o" optional="hide"/>' +
                    '<field name="amount"/>' +
                    '<field name="reference" optional="hide"/>' +
                '</tree>',
            services: {
                local_storage: RamStorageService,
            },
        });

        assert.containsN(list, 'th', 3,
            "should have 3 th, 1 for selector, 2 for columns");

        assert.containsOnce(list.$('table'), '.o_optional_columns_dropdown_toggle',
            "should have the optional columns dropdown toggle inside the table");

        // optional fields
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        assert.containsN(list, 'div.o_optional_columns div.dropdown-item', 2,
            "dropdown have 2 optional field foo with checked and bar with unchecked");

        // enable optional field
        await testUtils.dom.click(list.$('div.o_optional_columns div.dropdown-item:first input'));
        // 5 th (1 for checkbox, 4 for columns)
        assert.containsN(list, 'th', 4, "should have 4 th");
        assert.ok(list.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field

        // disable optional field
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        assert.strictEqual(list.$('div.o_optional_columns div.dropdown-item:first input:checked')[0],
            list.$('div.o_optional_columns div.dropdown-item [name="m2o"]')[0],
            "m2o advanced field check box should be checked in dropdown");

        await testUtils.dom.click(list.$('div.o_optional_columns div.dropdown-item:first input'));
        // 3 th (1 for checkbox, 2 for columns)
        assert.containsN(list, 'th', 3, "should have 3 th");
        assert.notOk(list.$('th:contains(M2O field)').is(':visible'),
            "should not have a visible m2o field"); //m2o field not displayed

        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        assert.notOk(list.$('div.o_optional_columns div.dropdown-item [name="m2o"]').is(":checked"));

        list.destroy();
    });

    QUnit.test('optinal fields do not disappear even after listview reload', async function (assert) {
        assert.expect(7);

        var RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="m2o" optional="hide"/>' +
                    '<field name="amount"/>' +
                    '<field name="reference" optional="hide"/>' +
                '</tree>',
            services: {
                local_storage: RamStorageService,
            },
        });

        assert.containsN(list, 'th', 3,
            "should have 3 th, 1 for selector, 2 for columns");

        // enable optional field
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        assert.notOk(list.$('div.o_optional_columns div.dropdown-item [name="m2o"]').is(":checked"));
        await testUtils.dom.click(list.$('div.o_optional_columns div.dropdown-item:first input'));
        assert.containsN(list, 'th', 4,
            "should have 4 th 1 for selector, 3 for columns");
        assert.ok(list.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field

        // reload listview
        await list.reload();
        assert.containsN(list, 'th', 4,
            "should have 4 th 1 for selector, 3 for columns ever after listview reload");
        assert.ok(list.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field even after listview reload");

        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        assert.ok(list.$('div.o_optional_columns div.dropdown-item [name="m2o"]').is(":checked"));

        list.destroy();
    });

    QUnit.test('change the viewType of the current action', async function (assert) {
        assert.expect(25);

        this.actions = [{
            id: 1,
            name: 'Partners Action 1',
            res_model: 'foo',
            type: 'ir.actions.act_window',
            views: [[1, 'kanban']],
        }, {
            id: 2,
            name: 'Partners',
            res_model: 'foo',
            type: 'ir.actions.act_window',
            views: [[false, 'list'], [1, 'kanban']],
        }];

        this.archs = {
            'foo,1,kanban': '<kanban><templates><t t-name="kanban-box">' +
            '<div class="oe_kanban_global_click"><field name="foo"/></div>' +
            '</t></templates></kanban>',

            'foo,false,list': '<tree limit="3">' +
            '<field name="foo"/>' +
            '<field name="m2o" optional="hide"/>' +
            '<field name="o2m" optional="show"/></tree>',

            'foo,false,search': '<search><field name="foo" string="Foo"/></search>',
        };

        var RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });

        var actionManager = await testUtils.createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            services: {
                local_storage: RamStorageService,
            },
        });
        await actionManager.doAction(2);

        assert.containsOnce(actionManager, '.o_list_view',
            "should have rendered a list view");

        assert.containsN(actionManager, 'th', 3, "should display 3 th (selector + 2 fields)");

        // enable optional field
        await testUtils.dom.click(actionManager.$('table .o_optional_columns_dropdown_toggle'));
        assert.notOk(actionManager.$('div.o_optional_columns div.dropdown-item [name="m2o"]').is(":checked"));
        assert.ok(actionManager.$('div.o_optional_columns div.dropdown-item [name="o2m"]').is(":checked"));
        await testUtils.dom.click(actionManager.$('div.o_optional_columns div.dropdown-item:first'));
        assert.containsN(actionManager, 'th', 4, "should display 4 th (selector + 3 fields)");
        assert.ok(actionManager.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field

        // switch to kanban view
        await actionManager.loadState({
            action: 2,
            view_type: 'kanban',
        });

        assert.containsNone(actionManager, '.o_list_view',
            "should not display the list view anymore");
        assert.containsOnce(actionManager, '.o_kanban_view',
            "should have switched to the kanban view");

        // switch back to list view
        await actionManager.loadState({
            action: 2,
            view_type: 'list',
        });

        assert.containsNone(actionManager, '.o_kanban_view',
            "should not display the kanban view anymoe");
        assert.containsOnce(actionManager, '.o_list_view',
            "should display the list view");

        assert.containsN(actionManager, 'th', 4, "should display 4 th");
        assert.ok(actionManager.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field
        assert.ok(actionManager.$('th:contains(O2M field)').is(':visible'),
            "should have a visible o2m field"); //m2o field

        // disable optional field
        await testUtils.dom.click(actionManager.$('table .o_optional_columns_dropdown_toggle'));
        assert.ok(actionManager.$('div.o_optional_columns div.dropdown-item [name="m2o"]').is(":checked"));
        assert.ok(actionManager.$('div.o_optional_columns div.dropdown-item [name="o2m"]').is(":checked"));
        await testUtils.dom.click(actionManager.$('div.o_optional_columns div.dropdown-item:last input'));
        assert.ok(actionManager.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field
        assert.notOk(actionManager.$('th:contains(O2M field)').is(':visible'),
            "should have a visible o2m field"); //m2o field
        assert.containsN(actionManager, 'th', 3, "should display 3 th");

        await actionManager.doAction(1);

        assert.containsNone(actionManager, '.o_list_view',
            "should not display the list view anymore");
        assert.containsOnce(actionManager, '.o_kanban_view',
            "should have switched to the kanban view");

        await actionManager.doAction(2);

        assert.containsNone(actionManager, '.o_kanban_view',
            "should not havethe kanban view anymoe");
        assert.containsOnce(actionManager, '.o_list_view',
            "should display the list view");

        assert.containsN(actionManager, 'th', 3, "should display 3 th");
        assert.ok(actionManager.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field
        assert.notOk(actionManager.$('th:contains(O2M field)').is(':visible'),
            "should have a visible o2m field"); //m2o field

        actionManager.destroy();
    });

    QUnit.test('list view with optional fields rendering and local storage mock', async function (assert) {
        assert.expect(12);

        var forceLocalStorage = true;

        var Storage = RamStorage.extend({
            getItem: function (key) {
                assert.step('getItem ' + key);
                return forceLocalStorage ? '["m2o"]' : this._super.apply(this, arguments);
            },
            setItem: function (key, value) {
                assert.step('setItem ' + key + ' to ' + value);
                return this._super.apply(this, arguments);
            },
        });

        var RamStorageService = AbstractStorageService.extend({
            storage: new Storage(),
        });

        var list = await createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                '<field name="foo"/>' +
                '<field name="m2o" optional="hide"/>' +
                '<field name="reference" optional="show"/>' +
                '</tree>',
            services: {
                local_storage: RamStorageService,
            },
        });

        assert.verifySteps(['getItem list_optional_fields,foo,list,foo:char,m2o:many2one,reference:reference']);

        assert.containsN(list, 'th', 3,
            "should have 3 th, 1 for selector, 2 for columns");

        assert.ok(list.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field

        assert.notOk(list.$('th:contains(Reference Field)').is(':visible'),
            "should not have a visible reference field");

        // optional fields
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        assert.containsN(list, 'div.o_optional_columns div.dropdown-item', 2,
            "dropdown have 2 optional fields");

        forceLocalStorage = false;
        // enable optional field
        await testUtils.dom.click(list.$('div.o_optional_columns div.dropdown-item:eq(1) input'));

        assert.verifySteps([
            'setItem list_optional_fields,foo,list,foo:char,m2o:many2one,reference:reference to ["m2o","reference"]',
            'getItem list_optional_fields,foo,list,foo:char,m2o:many2one,reference:reference',
        ]);

        // 4 th (1 for checkbox, 3 for columns)
        assert.containsN(list, 'th', 4, "should have 4 th");

        assert.ok(list.$('th:contains(M2O field)').is(':visible'),
            "should have a visible m2o field"); //m2o field

        assert.ok(list.$('th:contains(Reference Field)').is(':visible'),
            "should have a visible reference field");

        list.destroy();
    });

    // TODO: write test on:
    // - default_get with a field not in view
});

});
