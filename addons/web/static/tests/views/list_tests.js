odoo.define('web.list_tests', function (require) {
"use strict";

var config = require('web.config');
var basicFields = require('web.basic_fields');
var FormView = require('web.FormView');
var ListView = require('web.ListView');
var mixins = require('web.mixins');
var testUtils = require('web.test_utils');
var widgetRegistry = require('web.widget_registry');
var Widget = require('web.Widget');

var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "boolean"},
                    date: {string: "Some Date", type: "date"},
                    int_field: {string: "int_field", type: "integer", sortable: true},
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

    QUnit.test('simple readonly list', function (assert) {
        assert.expect(10);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="int_field"/></tree>',
        });

        assert.notOk(list.$el.hasClass('o_cannot_create'),
            "should not have className 'o_cannot_create'");

        // 3 th (1 for checkbox, 2 for columns)
        assert.strictEqual(list.$('th').length, 3, "should have 3 columns");

        assert.strictEqual(list.$('td:contains(gnap)').length, 1, "should contain gnap");
        assert.strictEqual(list.$('tbody tr').length, 4, "should have 4 rows");
        assert.strictEqual(list.$('th.o_column_sortable').length, 1, "should have 1 sortable column");

        assert.strictEqual(list.$('thead th:nth(2)').css('text-align'), 'right',
            "header cells of integer fields should be right aligned");
        assert.strictEqual(list.$('tbody tr:first td:nth(2)').css('text-align'), 'right',
            "integer cells should be right aligned");

        assert.ok(list.$buttons.find('.o_list_button_add').is(':visible'),
            "should have a visible Create button");
        assert.ok(!list.$buttons.find('.o_list_button_save').is(':visible'),
            "should not have a visible save button");
        assert.ok(!list.$buttons.find('.o_list_button_discard').is(':visible'),
            "should not have a visible save button");
        list.destroy();
    });

    QUnit.test('list with create="0"', function (assert) {
        assert.expect(2);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree create="0"><field name="foo"/></tree>',
        });

        assert.ok(list.$el.hasClass('o_cannot_create'),
            "should have className 'o_cannot_create'");
        assert.strictEqual(list.$buttons.find('.o_list_button_add').length, 0,
            "should not have the 'Create' button");

        list.destroy();
    });

    QUnit.test('list with delete="0"', function (assert) {
        assert.expect(4);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {sidebar: true},
            arch: '<tree delete="0"><field name="foo"/></tree>',
        });

        assert.ok(list.sidebar.$el.hasClass('o_hidden'), 'sidebar should be invisible');
        assert.ok(list.$('tbody td.o_list_record_selector').length, 'should have at least one record');

        list.$('tbody td.o_list_record_selector:first input').click();
        assert.ok(!list.sidebar.$el.hasClass('o_hidden'), 'sidebar should be visible');
        assert.notOk(list.sidebar.$('a:contains(Delete)').length, 'sidebar should not have Delete button');

        list.destroy();
    });

    QUnit.test('simple editable rendering', function (assert) {
        assert.expect(12);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.strictEqual(list.$('th').length, 3, "should have 2 th");
        assert.strictEqual(list.$('th').length, 3, "should have 3 th");
        assert.strictEqual(list.$('td:contains(yop)').length, 1, "should contain yop");

        assert.ok(list.$buttons.find('.o_list_button_add').is(':visible'),
            "should have a visible Create button");
        assert.ok(!list.$buttons.find('.o_list_button_save').is(':visible'),
            "should not have a visible save button");
        assert.ok(!list.$buttons.find('.o_list_button_discard').is(':visible'),
            "should not have a visible discard button");

        list.$('td:not(.o_list_record_selector)').first().click();

        assert.ok(!list.$buttons.find('.o_list_button_add').is(':visible'),
            "should not have a visible Create button");
        assert.ok(list.$buttons.find('.o_list_button_save').is(':visible'),
            "should have a visible save button");
        assert.ok(list.$buttons.find('.o_list_button_discard').is(':visible'),
            "should have a visible discard button");

        list.$buttons.find('.o_list_button_save').click();

        assert.ok(list.$buttons.find('.o_list_button_add').is(':visible'),
            "should have a visible Create button");
        assert.ok(!list.$buttons.find('.o_list_button_save').is(':visible'),
            "should not have a visible save button");
        assert.ok(!list.$buttons.find('.o_list_button_discard').is(':visible'),
            "should not have a visible discard button");
        list.destroy();
    });

    QUnit.test('invisible columns are not displayed', function (assert) {
        assert.expect(1);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="bar" invisible="1"/>' +
                '</tree>',
        });

        // 1 th for checkbox, 1 for 1 visible column
        assert.strictEqual(list.$('th').length, 2, "should have 2 th");
        list.destroy();
    });

    QUnit.test('record-depending invisible lines are correctly aligned', function (assert) {
        assert.expect(4);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="bar" attrs="{\'invisible\': [(\'id\',\'=\', 1)]}"/>' +
                    '<field name="int_field"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('tbody tr:first td').length, 4,
            "there should be 4 cells in the first row");
        assert.strictEqual(list.$('tbody td.o_invisible_modifier').length, 1,
            "there should be 1 invisible bar cell");
        assert.ok(list.$('tbody tr:first td:eq(2)').hasClass('o_invisible_modifier'),
            "the 3rd cell should be invisible");
        assert.strictEqual(list.$('tbody tr:eq(0) td:visible').length, list.$('tbody tr:eq(1) td:visible').length,
            "there should be the same number of visible cells in different rows");
        list.destroy();
    });

    QUnit.test('do not perform extra RPC to read invisible many2one fields', function (assert) {
        assert.expect(3);

        this.data.foo.fields.m2o.default = 2;

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="foo"/>' +
                    '<field name="m2o" invisible="1"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                assert.step(_.last(route.split('/')));
                return this._super.apply(this, arguments);
            },
        });

        list.$buttons.find('.o_list_button_add').click();
        assert.verifySteps(['search_read', 'default_get'], "no nameget should be done");

        list.destroy();
    });

    QUnit.test('at least 4 rows are rendered, even if less data', function (assert) {
        assert.expect(1);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="bar"/></tree>',
            domain: [['bar', '=', true]],
        });

        assert.strictEqual(list.$('tbody tr').length, 4, "should have 4 rows");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering', function (assert) {
        assert.expect(4);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
        });

        assert.strictEqual(list.$('th:contains(Foo)').length, 1, "should contain Foo");
        assert.strictEqual(list.$('th:contains(Bar)').length, 1, "should contain Bar");
        assert.strictEqual(list.$('tr.o_group_header').length, 2, "should have 2 .o_group_header");
        assert.strictEqual(list.$('th.o_group_name').length, 2, "should have 2 .o_group_name");
        list.destroy();
    });

    QUnit.test('many2one field rendering', function (assert) {
        assert.expect(1);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="m2o"/></tree>',
        });

        assert.ok(list.$('td:contains(Value 1)').length,
            "should have the display_name of the many2one");
        list.destroy();
    });

    QUnit.test('grouped list view, with 1 open group', function (assert) {
        assert.expect(6);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="int_field"/></tree>',
            groupBy: ['foo'],
        });

        list.$('th.o_group_name').get(1).click();
        assert.strictEqual(list.$('tbody:eq(1) tr').length, 2, "open group should contain 2 records");
        assert.strictEqual(list.$('tbody').length, 3, "should contain 3 tbody");
        assert.strictEqual(list.$('td:contains(9)').length, 1, "should contain 9");
        assert.strictEqual(list.$('td:contains(-4)').length, 1, "should contain -4");
        assert.strictEqual(list.$('td:contains(10)').length, 1, "should contain 10");
        assert.strictEqual(list.$('tr.o_group_header td:contains(10)').length, 1, "but 10 should be in a header");
        list.destroy();
    });

    QUnit.test('opening records when clicking on record', function (assert) {
        assert.expect(3);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
        });

        testUtils.intercept(list, "open_record", function () {
            assert.ok("list view should trigger 'open_record' event");
        });

        list.$('tr td:not(.o_list_record_selector)').first().click();
        list.update({groupBy: ['foo']});
        assert.strictEqual(list.$('tr.o_group_header').length, 3, "list should be grouped");
        list.$('th.o_group_name').first().click();

        list.$('tr:not(.o_group_header) td:not(.o_list_record_selector)').first().click();
        list.destroy();
    });

    QUnit.test('editable list view: readonly fields cannot be edited', function (assert) {
        assert.expect(4);

        this.data.foo.fields.foo.readonly = true;

        var list = createView({
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
        $td.click();
        assert.ok($td.parent().hasClass('o_selected_row'),
            "row should be in edit mode");
        assert.ok($td.hasClass('o_readonly_modifier'),
            "foo cell should be readonly in edit mode");
        assert.ok(!$second_td.hasClass('o_readonly_modifier'),
            "bar cell should be editable");
        assert.ok($third_td.hasClass('o_readonly_modifier'),
            "int_field cell should be readonly in edit mode");
        list.destroy();
    });

    QUnit.test('basic operations for editable list renderer', function (assert) {
        assert.expect(2);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        var $td = list.$('td:not(.o_list_record_selector)').first();
        assert.ok(!$td.parent().hasClass('o_selected_row'), "td should not be in edit mode");
        $td.click();
        assert.ok($td.parent().hasClass('o_selected_row'), "td should be in edit mode");
        list.destroy();
    });

    QUnit.test('editable list: add a line and discard', function (assert) {
        assert.expect(11);

        testUtils.patch(basicFields.FieldChar, {
            destroy: function () {
                assert.step('destroy');
                this._super.apply(this, arguments);
            },
        });

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
            domain: [['foo', '=', 'yop']],
        });

        assert.strictEqual(list.$('tbody tr').length, 4,
            "list should contain 4 rows");
        assert.strictEqual(list.$('.o_data_row').length, 1,
            "list should contain one record (and thus 3 empty rows)");
        assert.strictEqual(list.pager.$('.o_pager_value').text(), '1-1',
            "pager should be correct");

        list.$buttons.find('.o_list_button_add').click();

        assert.strictEqual(list.$('tbody tr').length, 4,
            "list should still contain 4 rows");
        assert.strictEqual(list.$('.o_data_row').length, 2,
            "list should contain two record (and thus 2 empty rows)");
        assert.strictEqual(list.pager.$('.o_pager_value').text(), '1-2',
            "pager should be correct");

        list.$buttons.find('.o_list_button_discard').click();

        assert.strictEqual(list.$('tbody tr').length, 4,
            "list should still contain 4 rows");
        assert.strictEqual(list.$('.o_data_row').length, 1,
            "list should contain one record (and thus 3 empty rows)");
        assert.strictEqual(list.pager.$('.o_pager_value').text(), '1-1',
            "pager should be correct");
        assert.verifySteps(['destroy'],
            "should have destroyed the widget of the removed line");

        testUtils.unpatch(basicFields.FieldChar);
        list.destroy();
    });

    QUnit.test('field changes are triggered correctly', function (assert) {
        assert.expect(2);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });
        var $td = list.$('td:not(.o_list_record_selector)').first();

        var n = 0;
        testUtils.intercept(list, "field_changed", function () {
            n += 1;
        });
        $td.click();
        $td.find('input').val('abc').trigger('input');
        assert.strictEqual(n, 1, "field_changed should have been triggered");
        list.$('td:not(.o_list_record_selector)').eq(2).click();
        assert.strictEqual(n, 1, "field_changed should not have been triggered");
        list.destroy();
    });

    QUnit.test('editable list view: basic char field edition', function (assert) {
        assert.expect(4);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });
        var $td = list.$('td:not(.o_list_record_selector)').first();
        $td.click();
        $td.find('input').val('abc').trigger('input');
        assert.strictEqual($td.find('input').val(), 'abc', "char field has been edited correctly");

        var $next_row_td = list.$('tbody tr:eq(1) td:not(.o_list_record_selector)').first();
        $next_row_td.click(); // should trigger the save of the previous row
        assert.strictEqual(list.$('td:not(.o_list_record_selector)').first().text(), 'abc',
            'changes should be saved correctly');
        assert.ok(!list.$('tbody tr').first().hasClass('o_selected_row'),
            'saved row should be in readonly mode');
        assert.strictEqual(this.data.foo.records[0].foo, 'abc',
            "the edition should have been properly saved");
        list.destroy();
    });

    QUnit.test('editable list view: save data when list sorting in edit mode', function (assert) {
        assert.expect(3);

        this.data.foo.fields.foo.sortable = true;

        var list = createView({
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
            }
        });

        list.$('.o_data_cell:first').click();
        list.$('input[name="foo"]').val('xyz').trigger('input');
        list.$('.o_column_sortable').click();

        assert.ok(list.$('.o_data_row:first').hasClass('o_selected_row'),
            "first row should still be in edition");

        list.$buttons.find('.o_list_button_save').click();
        assert.ok(!list.$buttons.hasClass('o-editing'),
            "list buttons should be back to their readonly mode");

        list.destroy();
    });

    QUnit.test('selection changes are triggered correctly', function (assert) {
        assert.expect(8);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
        });
        var $tbody_selector = list.$('tbody .o_list_record_selector input').first();
        var $thead_selector = list.$('thead .o_list_record_selector input');

        var n = 0;
        testUtils.intercept(list, "selection_changed", function () {
            n += 1;
        });

        // tbody checkbox click
        $tbody_selector.click();
        assert.strictEqual(n, 1, "selection_changed should have been triggered");
        assert.ok($tbody_selector.is(':checked'), "selection checkbox should be checked");
        $tbody_selector.click();
        assert.strictEqual(n, 2, "selection_changed should have been triggered");
        assert.ok(!$tbody_selector.is(':checked'), "selection checkbox shouldn't be checked");

        // head checkbox click
        $thead_selector.click();
        assert.strictEqual(n, 3, "selection_changed should have been triggered");
        assert.strictEqual(list.$('tbody .o_list_record_selector input:checked').length,
            list.$('tbody tr').length, "all selection checkboxes should be checked");

        $thead_selector.click();
        assert.strictEqual(n, 4, "selection_changed should have been triggered");

        assert.strictEqual(list.$('tbody .o_list_record_selector input:checked').length, 0,
                            "no selection checkbox should be checked");
        list.destroy();
    });

    QUnit.test('selection is reset on reload', function (assert) {
        assert.expect(5);

        var list = createView({
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
        $firstRowSelector.click();
        assert.ok($firstRowSelector.is(':checked'), "first row should be selected");
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), '10',
            "total should be 10 (first record selected)");

        // reload
        list.reload();
        $firstRowSelector = list.$('tbody .o_list_record_selector input').first();
        assert.notOk($firstRowSelector.is(':checked'),
            "first row should no longer be selected");
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), '32',
            "total should be 32 (no more record selected)");

        list.destroy();
    });

    QUnit.test('selection is kept on render without reload', function (assert) {
        assert.expect(5);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            groupBy: ['foo'],
            viewOptions: {sidebar: true},
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="int_field" sum="Sum"/>' +
                '</tree>',
        });

        // open blip grouping and check all lines
        list.$('.o_group_header:contains("blip (2)")').click();
        list.$('.o_data_row input').click();
        assert.strictEqual(true, list.sidebar.$el.is(':visible'),
            "element checked so sidebar")

        // open yop grouping and verify blip are still checked
        list.$('.o_group_header:contains("yop (1)")').click()
        assert.strictEqual(2, list.$('.o_data_row input:checked').length,
            "opening a grouping does not uncheck others");
        assert.strictEqual(true, list.sidebar.$el.is(':visible'),
            "element checked so sidebar")

        // close and open blip grouping and verify blip are unchecked
        list.$('.o_group_header:contains("blip (2)")').click();
        list.$('.o_group_header:contains("blip (2)")').click();
        assert.strictEqual(0, list.$('.o_data_row input:checked').length,
            "opening and closing a grouping uncheck its elements");
        assert.strictEqual(false, list.sidebar.$el.is(':visible'),
            "no element checked so no sidebar")

        list.destroy();
    });

    QUnit.test('aggregates are computed correctly', function (assert) {
        assert.expect(4);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field" sum="Sum"/></tree>',
        });
        var $tbody_selectors = list.$('tbody .o_list_record_selector input');
        var $thead_selector = list.$('thead .o_list_record_selector input');

        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "32", "total should be 32");

        $tbody_selectors.first().click();
        $tbody_selectors.last().click();
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "6",
                        "total should be 6 as first and last records are selected");

        $thead_selector.click();
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "32",
                        "total should be 32 as all records are selected");

        // Let's update the view to dislay NO records
        list.update({domain: ['&', ['bar', '=', false], ['int_field', '>', 0]]});
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "0", "total should have been recomputed to 0");

        list.destroy();
    });

    QUnit.test('aggregates are computed correctly in grouped lists', function (assert) {
        assert.expect(4);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            groupBy: ['m2o'],
            arch: '<tree editable="bottom"><field name="int_field" sum="Sum"/></tree>',
        });

        var $groupHeader1 = list.$('.o_group_header').filter(function (index, el) {
            return $(el).data('group').res_id === 1;
        });
        var $groupHeader2 = list.$('.o_group_header').filter(function (index, el) {
            return $(el).data('group').res_id === 2;
        });
        assert.strictEqual($groupHeader1.find('td:nth(1)').text(), "23", "first group total should be 23");
        assert.strictEqual($groupHeader2.find('td:nth(1)').text(), "9", "second group total should be 9");
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "32", "total should be 32");

        $groupHeader1.click();
        list.$('tbody .o_list_record_selector input').first().click();
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "10",
                        "total should be 10 as first record of first group is selected");
        list.destroy();
    });

    QUnit.test('aggregates are updated when a line is edited', function (assert) {
        assert.expect(2);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="int_field" sum="Sum"/></tree>',
        });

        assert.strictEqual(list.$('td[title="Sum"]').text(), "32", "current total should be 32");

        list.$('tr.o_data_row td.o_data_cell').first().click();
        list.$('td.o_data_cell input').val("15").trigger("input");

        assert.strictEqual(list.$('td[title="Sum"]').text(), "37",
            "current total should now be 37");
        list.destroy();
    });

    QUnit.test('aggregates are formatted according to field widget', function (assert) {
        assert.expect(1);

        var list = createView({
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

    QUnit.test('groups can be sorted on aggregates', function (assert) {
        assert.expect(10);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            groupBy: ['foo'],
            arch: '<tree editable="bottom"><field name="int_field" sum="Sum"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.step(args.kwargs.orderby || 'default order');
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(list.$('tbody .o_list_number').text(), '10517',
            "initial order should be 10, 5, 17");
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), '32', "total should be 32");

        list.$('.o_column_sortable').click(); // sort (int_field ASC)
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), '32', "total should still be 32");
        assert.strictEqual(list.$('tbody .o_list_number').text(), '51017',
            "order should be 5, 10, 17");

        list.$('.o_column_sortable').click(); // sort (int_field DESC)
        assert.strictEqual(list.$('tbody .o_list_number').text(), '17105',
            "initial order should be 17, 10, 5");
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), '32', "total should still be 32");

        assert.verifySteps(['default order', 'int_field ASC', 'int_field DESC']);

        list.destroy();
    });

    QUnit.test('properly apply onchange in simple case', function (assert) {
        assert.expect(2);

        this.data.foo.onchanges = {
            foo: function (obj) {
                obj.int_field = obj.foo.length + 1000;
            },
        };
        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="int_field"/></tree>',
        });

        var $foo_td = list.$('td:not(.o_list_record_selector)').first();
        var $int_field_td = list.$('td:not(.o_list_record_selector)').eq(1);

        assert.strictEqual($int_field_td.text(), '10', "should contain initial value");

        $foo_td.click();
        $foo_td.find('input').val('tralala').trigger('input');

        assert.strictEqual($int_field_td.find('input').val(), "1007",
                        "should contain input with onchange applied");
        list.destroy();
    });

    QUnit.test('column width should not change when switching mode', function (assert) {
        assert.expect(10);

        // Warning: this test is css dependant
        var list = createView({
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

        // start edition of first row
        list.$('td:not(.o_list_record_selector)').first().click();

        var editionWidths = _.pluck(list.$('thead th'), 'offsetWidth');

        // leave edition
        list.$buttons.find('.o_list_button_save').click();
        var readonlyWidths = _.pluck(list.$('thead th'), 'offsetWidth');

        for (var i = 0; i < startWidths.length; i++) {
            assert.strictEqual(startWidths[i], editionWidths[i],
                'width of columns should remain unchanged which switching from readonly to edit mode');
            assert.strictEqual(editionWidths[i], readonlyWidths[i],
                'width of columns should remain unchanged which switching from edit to readonly mode');
        }
        list.destroy();
    });

    QUnit.test('deleting one record', function (assert) {
        assert.expect(5);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {sidebar: true},
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.ok(list.sidebar.$el.hasClass('o_hidden'), 'sidebar should be invisible');
        assert.strictEqual(list.$('tbody td.o_list_record_selector').length, 4, "should have 4 records");

        list.$('tbody td.o_list_record_selector:first input').click();

        assert.ok(!list.sidebar.$el.hasClass('o_hidden'), 'sidebar should be visible');

        list.sidebar.$('a:contains(Delete)').click();
        assert.ok($('body').hasClass('modal-open'), 'body should have modal-open clsss');

        $('body .modal-dialog button span:contains(Ok)').click();

        assert.strictEqual(list.$('tbody td.o_list_record_selector').length, 3, "should have 3 records");
        list.destroy();
    });

    QUnit.test('archiving one record', function (assert) {
        assert.expect(9);

        // add active field on foo model and make all records active
        this.data.foo.fields.active = {string: 'Active', type: 'boolean', default: true};

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {sidebar: true},
            arch: '<tree><field name="foo"/></tree>',
            mockRPC: function (route) {
                if (route === '/web/dataset/call_kw/ir.attachment/search_read') {
                    return $.when([]);
                }
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(list.sidebar.$el.hasClass('o_hidden'), 'sidebar should be invisible');
        assert.strictEqual(list.$('tbody td.o_list_record_selector').length, 4, "should have 4 records");

        list.$('tbody td.o_list_record_selector:first input').click();

        assert.ok(!list.sidebar.$el.hasClass('o_hidden'), 'sidebar should be visible');

        assert.verifySteps(['/web/dataset/search_read']);
        list.sidebar.$('a:contains(Archive)').click();

        assert.strictEqual(list.$('tbody td.o_list_record_selector').length, 3, "should have 3 records");
        assert.verifySteps(['/web/dataset/search_read', '/web/dataset/call_kw/foo/write', '/web/dataset/search_read']);
        list.destroy();
    });

    QUnit.test('pager (ungrouped and grouped mode), default limit', function (assert) {
        assert.expect(4);

        var list = createView({
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

        assert.ok(!list.pager.$el.hasClass('o_hidden'), "pager should be visible");
        assert.strictEqual(list.pager.state.size, 4, "pager's size should be 4");
        list.update({ groupBy: ['bar']});
        assert.ok(list.pager.$el.hasClass('o_hidden'), "pager should be invisible");
        list.destroy();
    });

    QUnit.test('can sort records when clicking on header', function (assert) {
        assert.expect(9);

        this.data.foo.fields.foo.sortable = true;

        var nbSearchRead = 0;
        var list = createView({
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
        list.$('thead th:contains(Foo)').click();
        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.ok(list.$('tbody tr:first td:contains(blip)').length,
            "record 3 should be first");
        assert.ok(list.$('tbody tr:eq(3) td:contains(yop)').length,
            "record 1 should be first");

        nbSearchRead = 0;
        list.$('thead th:contains(Foo)').click();
        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.ok(list.$('tbody tr:first td:contains(yop)').length,
            "record 3 should be first");
        assert.ok(list.$('tbody tr:eq(3) td:contains(blip)').length,
            "record 1 should be first");

        list.destroy();
    });

    QUnit.test('use default_order', function (assert) {
        assert.expect(3);

        var list = createView({
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

    QUnit.test('use more complex default_order', function (assert) {
        assert.expect(3);

        var list = createView({
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

    QUnit.test('use default_order on editable tree: sort on save', function (assert) {
        assert.expect(8);

        this.data.foo.records[0].o2m = [1, 3];

        var form = createView({
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

        form.$buttons.find('.o_form_button_edit').click();
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");

        var $o2m = form.$('.o_field_widget[name=o2m]');
        form.$('.o_field_x2many_list_row_add a').click();
        $o2m.find('.o_field_widget').val("Value 2").trigger('input');
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");
        assert.ok(form.$('tbody tr:eq(2) td input').val(),
            "Value 2 should be third (shouldn't be sorted)");

        form.$buttons.find('.o_form_button_save').click();
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 2)').length,
            "Value 2 should be second (should be sorted after saving)");
        assert.ok(form.$('tbody tr:eq(2) td:contains(Value 3)').length,
            "Value 3 should be third");

        form.destroy();
    });

    QUnit.test('use default_order on editable tree: sort on demand', function (assert) {
        assert.expect(11);

        this.data.foo.records[0].o2m = [1, 3];
        this.data.bar.fields = {name: {string: "Name", type: "char", sortable: true}};
        this.data.bar.records[0].name = "Value 1";
        this.data.bar.records[2].name = "Value 3";

        var form = createView({
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

        form.$buttons.find('.o_form_button_edit').click();
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");

        var $o2m = form.$('.o_field_widget[name=o2m]');
        form.$('.o_field_x2many_list_row_add a').click();
        $o2m.find('.o_field_widget').val("Value 2").trigger('input');
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");
        assert.ok(form.$('tbody tr:eq(2) td input').val(),
            "Value 2 should be third (shouldn't be sorted)");

        form.$('.o_form_sheet_bg').click(); // validate the row before sorting

        $o2m.find('.o_column_sortable').click(); // resort list after edition
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 1',
            "Value 1 should be first");
        assert.strictEqual(form.$('tbody tr:eq(1)').text(), 'Value 2',
            "Value 2 should be second (should be sorted after saving)");
        assert.strictEqual(form.$('tbody tr:eq(2)').text(), 'Value 3',
            "Value 3 should be third");

        $o2m.find('.o_column_sortable').click();
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 3',
            "Value 3 should be first");
        assert.strictEqual(form.$('tbody tr:eq(1)').text(), 'Value 2',
            "Value 2 should be second (should be sorted after saving)");
        assert.strictEqual(form.$('tbody tr:eq(2)').text(), 'Value 1',
            "Value 1 should be third");

        form.destroy();
    });

    QUnit.test('use default_order on editable tree: sort on demand in page', function (assert) {
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

        var form = createView({
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
        form.$('.o_pager_next').click();
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 44',
            "record 44 should be first");
        assert.strictEqual(form.$('tbody tr:eq(4)').text(), 'Value 48',
            "record 48 should be last");

        form.$('.o_column_sortable').click();
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 08',
            "record 48 should be first");
        assert.strictEqual(form.$('tbody tr:eq(4)').text(), 'Value 04',
            "record 44 should be first");

        form.destroy();
    });

    QUnit.test('can display button in edit mode', function (assert) {
        assert.expect(2);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<button name="notafield" type="object" icon="fa-asterisk" class="o_yeah"/>' +
                '</tree>',
        });
        assert.ok(list.$('tbody button').length, "should have a button");
        assert.ok(list.$('tbody button').hasClass('o_yeah'), "class should be set on the button");
        list.destroy();
    });

    QUnit.test('can display a list with a many2many field', function (assert) {
        assert.expect(3);

        var list = createView({
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

    QUnit.test('list without import button', function (assert) {
        assert.expect(1);

        var list = createView({
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

    QUnit.test('display a tooltip on a field', function (assert) {
        assert.expect(2);

        var initialDebugMode = config.debug;
        config.debug = false;

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
        });

        // this is done to force the tooltip to show immediately instead of waiting
        // 1000 ms. not totally academic, but a short test suite is easier to sell :(
        list.$('th:not(.o_list_record_selector)').tooltip('show', false);

        list.$('th:not(.o_list_record_selector)').trigger($.Event('mouseenter'));
        assert.strictEqual($('.tooltip .oe_tooltip_string').length, 0, "should not have rendered a tooltip");

        config.debug = true;
        // it is necessary to rerender the list so tooltips can be properly created
        list.reload();
        list.$('th:not(.o_list_record_selector)').tooltip('show', false);

        list.$('th:not(.o_list_record_selector)').trigger($.Event('mouseenter'));
        assert.strictEqual($('.tooltip .oe_tooltip_string').length, 1, "should have rendered a tooltip");

        config.debug = initialDebugMode;
        list.destroy();
    });

    QUnit.test('support row decoration', function (assert) {
        assert.expect(2);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree decoration-info="int_field > 5">' +
                    '<field name="foo"/><field name="int_field"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('tbody tr.text-info').length, 3,
            "should have 3 columns with text-info class");

        assert.strictEqual(list.$('tbody tr').length, 4, "should have 4 rows");
        list.destroy();
    });

    QUnit.test('support row decoration (with unset numeric values)', function (assert) {
        assert.expect(2);

        this.data.foo.records = [];

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom" decoration-danger="int_field &lt; 0">' +
                    '<field name="int_field"/>' +
                '</tree>',
        });

        list.$buttons.find('.o_list_button_add').click();

        assert.strictEqual(list.$('tr.o_data_row.text-danger').length, 0,
            "the data row should not have .text-danger decoration (int_field is unset)");
        list.$('input[name="int_field"]').val('-3').trigger('input');
        assert.strictEqual(list.$('tr.o_data_row.text-danger').length, 1,
            "the data row should have .text-danger decoration (int_field is negative)");
        list.destroy();
    });

    QUnit.test('support row decoration with date', function (assert) {
        assert.expect(3);

        this.data.foo.records[0].datetime = '2017-02-27 12:51:35';

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree decoration-info="datetime == \'2017-02-27 12:51:35\'" decoration-danger="datetime &gt; \'2017-02-27 12:51:35\' AND datetime &lt; \'2017-02-27 10:51:35\'">' +
                    '<field name="datetime"/><field name="int_field"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('tbody tr.text-info').length, 1,
            "should have 1 columns with text-info class with good datetime");

        assert.strictEqual(list.$('tbody tr.text-danger').length, 0,
            "should have 0 columns with text-danger class with wrong timezone datetime");

        assert.strictEqual(list.$('tbody tr').length, 4, "should have 4 rows");
        list.destroy();
    });

    QUnit.test('no content helper when no data', function (assert) {
        assert.expect(5);

        var records = this.data.foo.records;

        this.data.foo.records = [];

        var list = createView({
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

        assert.strictEqual(list.$('.oe_view_nocontent').length, 1,
            "should display the no content helper");

        assert.strictEqual(list.$('table').length, 0, "should not have a table in the dom");

        assert.strictEqual(list.$('.oe_view_nocontent p.hello:contains(add a partner)').length, 1,
            "should have rendered no content helper from action");

        this.data.foo.records = records;
        list.reload();

        assert.strictEqual(list.$('.oe_view_nocontent').length, 0,
            "should not display the no content helper");
        assert.strictEqual(list.$('table').length, 1, "should have a table in the dom");
        list.destroy();
    });

    QUnit.test('no nocontent helper when no data and no help', function (assert) {
        assert.expect(3);

        this.data.foo.records = [];

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.strictEqual(list.$('.oe_view_nocontent').length, 0,
            "should not display the no content helper");

        assert.strictEqual(list.$('tr.o_data_row').length, 0,
            "should not have any data row");

        assert.strictEqual(list.$('table').length, 1, "should have a table in the dom");
        list.destroy();
    });

    QUnit.test('list view, editable, without data', function (assert) {
        assert.expect(11);

        this.data.foo.records = [];

        this.data.foo.fields.date.default = "2017-02-10";

        var list = createView({
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

        assert.strictEqual(list.$('.oe_view_nocontent').length, 1,
            "should have a no content helper displayed");

        assert.strictEqual(list.$('div.table-responsive').length, 0,
            "should not have a div.table-responsive");
        assert.strictEqual(list.$('table').length, 0, "should not have rendered a table");

        list.$buttons.find('.o_list_button_add').click();

        assert.strictEqual(list.$('.oe_view_nocontent').length, 0,
            "should not have a no content helper displayed");
        assert.strictEqual(list.$('table').length, 1, "should have rendered a table");
        assert.strictEqual(list.$el.css('height'), list.$('div.table-responsive').css('height'),
            "the div for the table should take the full height");


        assert.ok(list.$('tbody tr:eq(0)').hasClass('o_selected_row'),
            "the date field td should be in edit mode");
        assert.strictEqual(list.$('tbody tr:eq(0) td:eq(1)').text().trim(), "",
            "the date field td should not have any content");

        assert.strictEqual(list.$('.o_list_button button').prop('disabled'), true,
            "buttons should be disabled while the record is not yet created");

        list.$buttons.find('.o_list_button_save').click();

        assert.strictEqual(list.$('.o_list_button button').prop('disabled'), false,
            "buttons should not be disabled once the record is created");

        list.destroy();
    });

    QUnit.test('list view, editable, with a button', function (assert) {
        assert.expect(1);

        this.data.foo.records = [];

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="foo"/>' +
                    '<button string="abc" icon="fa-phone" type="object" name="schedule_another_phonecall"/>' +
                '</tree>',
        });

        list.$buttons.find('.o_list_button_add').click();

        assert.strictEqual(list.$('table button.o_icon_button i.fa-phone').length, 1,
            "should have rendered a button");
        list.destroy();
    });

    QUnit.test('list view with a button without icon', function (assert) {
        assert.expect(1);

        var list = createView({
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

    QUnit.test('list view, editable, can discard', function (assert) {
        assert.expect(5);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree string="Phonecalls" editable="top">' +
                    '<field name="foo"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('td:not(.o_list_record_selector) input').length, 0, "no input should be in the table");

        list.$('tbody td:not(.o_list_record_selector):first').click();
        assert.strictEqual(list.$('td:not(.o_list_record_selector) input').length, 1, "first cell should be editable");

        assert.ok(list.$buttons.find('.o_list_button_discard').is(':visible'),
            "discard button should be visible");

        list.$buttons.find('.o_list_button_discard').click();

        assert.strictEqual(list.$('td:not(.o_list_record_selector) input').length, 0, "no input should be in the table");

        assert.ok(!list.$buttons.find('.o_list_button_discard').is(':visible'),
            "discard button should not be visible");
        list.destroy();
    });

    QUnit.test('editable list view, click on the list to save', function (assert) {
        assert.expect(3);

        this.data.foo.fields.date.default = "2017-02-10";
        this.data.foo.records = [];

        var createCount = 0;

        var list = createView({
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

        list.$buttons.find('.o_list_button_add').click();
        list.$('div.table-responsive').click();

        assert.strictEqual(createCount, 1, "should have created a record");

        list.$buttons.find('.o_list_button_add').click();
        list.$('tfoot').click();

        assert.strictEqual(createCount, 2, "should have created a record");

        list.$buttons.find('.o_list_button_add').click();
        list.$('tbody tr').last().click();

        assert.strictEqual(createCount, 3, "should have created a record");
        list.destroy();
    });

    QUnit.test('click on a button in a list view', function (assert) {
        assert.expect(9);

        var list = createView({
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

        assert.strictEqual(list.$('.o_list_button').length, 4,
            "there should be one button per row");
        assert.strictEqual(list.$('.o_list_button:first .o_icon_button .fa.fa-car').length, 1,
            'buttons should have correct icon');

        list.$('.o_list_button:first > button').click(); // click on the button
        assert.verifySteps(['/web/dataset/search_read', '/web/dataset/search_read'],
            "should have reloaded the view (after the action is complete)");
        list.destroy();
    });

    QUnit.test('invisible attrs in readonly and editable list', function (assert) {
        assert.expect(5);

        var list = createView({
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
        list.$('tbody tr:nth(0) td:nth(2)').click(); // click on first row to edit it
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(4) input.o_invisible_modifier').length, 1,
            "td that contains an invisible field should not be empty in edition");
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > button.o_invisible_modifier').length, 1,
            "td that contains an invisible button should not be empty in edition");
        list.$buttons.find('.o_list_button_discard').click(); // leave edition

        // click on the invisible field's cell to edit first row
        list.$('tbody tr:nth(0) td:nth(4)').click();
        assert.ok(list.$('tbody tr:nth(0)').hasClass('o_selected_row'),
            "first row should be in edition");
        list.destroy();
    });

    QUnit.test('monetary fields are properly rendered', function (assert) {
        assert.expect(3);

        var currencies = {};
        _.each(this.data.res_currency.records, function (currency) {
            currencies[currency.id] = currency;
        });
        var list = createView({
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

        assert.strictEqual(list.$('tbody tr:first td').length, 3,
            "currency_id column should not be in the table");
        assert.strictEqual(list.$('tbody tr:first td:nth(2)').text().replace(/\s/g, ' '),
            '1200.00 €', "currency_id column should not be in the table");
        assert.strictEqual(list.$('tbody tr:nth(1) td:nth(2)').text().replace(/\s/g, ' '),
            '$ 500.00', "currency_id column should not be in the table");

        list.destroy();
    });

    QUnit.test('simple list with date and datetime', function (assert) {
        assert.expect(2);

        var list = createView({
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

    QUnit.test('edit a row by clicking on a readonly field', function (assert) {
        assert.expect(8);

        this.data.foo.fields.foo.readonly = true;

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
        });

        assert.ok(list.$('.o_data_row:first td:nth(1)').hasClass('o_readonly_modifier'),
            "foo field cells should have class 'o_readonly_modifier'");

        // edit the first row
        list.$('.o_data_row:first td:nth(1)').click();
        assert.ok(list.$('.o_data_row:first').hasClass('o_selected_row'),
            "first row should be selected");
        var $cell = list.$('.o_data_row:first td:nth(1)');
        assert.ok($cell.hasClass('o_readonly_modifier') && $cell.parent().hasClass('o_selected_row'),
            "foo field cells should have class 'o_readonly_modifier' and the row should be in edition");
        assert.strictEqual(list.$('.o_data_row:first td:nth(1) span').text(), 'yop',
            "a widget should have been rendered for readonly fields");
        assert.ok(list.$('.o_data_row:first td:nth(2)').parent().hasClass('o_selected_row'),
            "field 'int_field' should be in edition");
        assert.strictEqual(list.$('.o_data_row:first td:nth(2) input').length, 1,
            "a widget for field 'int_field should have been rendered'");

        // click again on readonly cell of first line: nothing should have changed
        list.$('.o_data_row:first td:nth(1)').click();
        assert.ok(list.$('.o_data_row:first').hasClass('o_selected_row'),
            "first row should be selected");
        assert.strictEqual(list.$('.o_data_row:first td:nth(2) input').length, 1,
            "a widget for field 'int_field' should have been rendered (only once)");

        list.destroy();
    });

    QUnit.test('list view with nested groups', function (assert) {
        assert.expect(42);

        this.data.foo.records.push({id: 5, foo: "blip", int_field: -7, m2o: 1});
        this.data.foo.records.push({id: 6, foo: "blip", int_field: 5, m2o: 2});

        var nbRPCs = {readGroup: 0, searchRead: 0};
        var envIDs = []; // the ids that should be in the environment during this test

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="id"/><field name="int_field"/></tree>',
            groupBy: ['m2o', 'foo'],
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
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
                env_updated: function (event) {
                    assert.deepEqual(event.data.ids, envIDs,
                        "should notify the environment with the correct ids");
                },
            },
        });

        assert.strictEqual(nbRPCs.readGroup, 1, "should have done one read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");

        // basic rendering tests
        assert.strictEqual(list.$('tbody').length, 1, "there should be 1 tbody");
        assert.strictEqual(list.$('.o_group_header').length, 2,
            "should contain 2 groups at first level");
        assert.strictEqual(list.$('.o_group_name:first').text(), 'Value 1 (4)',
            "group should have correct name and count");
        assert.strictEqual(list.$('.o_group_name .fa-caret-right').length, 2,
            "the carret of closed groups should be right");
        assert.strictEqual(list.$('.o_group_name:first span').css('padding-left'),
            '0px', "groups of level 1 should have a 0px padding-left");
        assert.strictEqual(list.$('.o_group_header:first td:last').text(), '16',
            "group aggregates are correctly displayed");

        // open the first group
        nbRPCs = {readGroup: 0, searchRead: 0};
        list.$('.o_group_header:first').click();
        assert.strictEqual(nbRPCs.readGroup, 1, "should have done one read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");

        var $openGroup = list.$('tbody:nth(1)');
        assert.strictEqual(list.$('.o_group_name:first').text(), 'Value 1 (4)',
            "group should have correct name and count (of records, not inner subgroups)");
        assert.strictEqual(list.$('tbody').length, 3, "there should be 3 tbodys");
        assert.strictEqual(list.$('.o_group_name:first .fa-caret-down').length, 1,
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
        $openGroup.find('.o_group_header:nth(2)').click();
        assert.strictEqual(nbRPCs.readGroup, 0, "should have done no read_group");
        assert.strictEqual(nbRPCs.searchRead, 1, "should have done one search_read");

        var $openSubGroup = list.$('tbody:nth(2)');
        assert.strictEqual(list.$('tbody').length, 4, "there should be 4 tbodys");
        assert.strictEqual($openSubGroup.find('.o_data_row').length, 2,
            "open subgroup should contain 2 data rows");
        assert.strictEqual($openSubGroup.find('.o_data_row:first td:last').text(), '-4',
            "first record in open subgroup should be res_id 4 (with int_field -4)");

        // open a record (should trigger event 'open_record')
        $openSubGroup.find('.o_data_row:first').click();

        // sort by int_field (ASC) and check that open groups are still open
        nbRPCs = {readGroup: 0, searchRead: 0};
        envIDs = [5, 4]; // order of the records changed
        list.$('thead th:last').click();
        assert.strictEqual(nbRPCs.readGroup, 2, "should have done two read_groups");
        assert.strictEqual(nbRPCs.searchRead, 1, "should have done one search_read");

        $openSubGroup = list.$('tbody:nth(2)');
        assert.strictEqual(list.$('tbody').length, 4, "there should be 4 tbodys");
        assert.strictEqual($openSubGroup.find('.o_data_row').length, 2,
            "open subgroup should contain 2 data rows");
        assert.strictEqual($openSubGroup.find('.o_data_row:first td:last').text(), '-7',
            "first record in open subgroup should be res_id 5 (with int_field -7)");

        // close first level group
        nbRPCs = {readGroup: 0, searchRead: 0};
        envIDs = []; // the group being closed, there is no more record in the environment
        list.$('.o_group_header:nth(1)').click();
        assert.strictEqual(nbRPCs.readGroup, 0, "should have done no read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");

        assert.strictEqual(list.$('tbody').length, 1, "there should be 1 tbody");
        assert.strictEqual(list.$('.o_group_header').length, 2,
            "should contain 2 groups at first level");
        assert.strictEqual(list.$('.o_group_name .fa-caret-right').length, 2,
            "the carret of closed groups should be right");

        list.destroy();
    });

    QUnit.test('grouped list on selection field at level 2', function (assert) {
        assert.expect(4);

        this.data.foo.fields.priority = {
            string: "Priority",
            type: "selection",
            selection: [[1, "Low"], [2, "Medium"], [3, "High"]],
            default: 1,
        };
        this.data.foo.records.push({id: 5, foo: "blip", int_field: -7, m2o: 1, priority: 2});
        this.data.foo.records.push({id: 6, foo: "blip", int_field: 5, m2o: 1, priority: 3});

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="id"/><field name="int_field"/></tree>',
            groupBy: ['m2o', 'priority'],
        });

        assert.strictEqual(list.$('.o_group_header').length, 2,
            "should contain 2 groups at first level");

        // open the first group
        list.$('.o_group_header:first').click();

        var $openGroup = list.$('tbody:nth(1)');
        assert.strictEqual($openGroup.find('tr').length, 3,
            "should have 3 subgroups");
        assert.strictEqual($openGroup.find('tr').length, 3,
            "should have 3 subgroups");
        assert.strictEqual($openGroup.find('.o_group_name:first').text(), 'Low (3)',
            "should display the selection name in the group header");

        list.destroy();
    });

    QUnit.test('grouped list with a pager in a group', function (assert) {
        assert.expect(6);
        this.data.foo.records[3].bar = true;

        var list = createView({
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
        list.$('.o_group_header').click();
        assert.strictEqual(list.$('.o_group_header').css('height'), headerHeight,
            "height of group header shouldn't have changed");
        assert.ok(list.$('.o_group_header td:last').hasClass('o_group_pager'),
            "last cell of open group header should have classname 'o_group_header'");
        assert.strictEqual(list.$('.o_pager_value').text(), '1-3',
            "pager's value should be correct");
        assert.strictEqual(list.$('.o_data_row').length, 3,
            "open group should display 3 records");

        // go to next page
        list.$('.o_pager_next').click();
        assert.strictEqual(list.$('.o_pager_value').text(), '4-4',
            "pager's value should be correct");
        assert.strictEqual(list.$('.o_data_row').length, 1,
            "open group should display 1 record");

        list.destroy();
    });

    QUnit.test('edition: create new line, then discard', function (assert) {
        assert.expect(8);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        assert.strictEqual(list.$('tr.o_data_row').length, 4,
            "should have 4 records");
        assert.strictEqual(list.$buttons.find('.o_list_button_add:visible').length, 1,
            "create button should be visible");
        assert.strictEqual(list.$buttons.find('.o_list_button_discard:visible').length, 0,
            "discard button should be hidden");
        list.$buttons.find('.o_list_button_add').click();
        assert.strictEqual(list.$buttons.find('.o_list_button_add:visible').length, 0,
            "create button should be hidden");
        assert.strictEqual(list.$buttons.find('.o_list_button_discard:visible').length, 1,
            "discard button should be visible");
        list.$buttons.find('.o_list_button_discard').click();
        assert.strictEqual(list.$('tr.o_data_row').length, 4,
            "should still have 4 records");
        assert.strictEqual(list.$buttons.find('.o_list_button_add:visible').length, 1,
            "create button should be visible again");
        assert.strictEqual(list.$buttons.find('.o_list_button_discard:visible').length, 0,
            "discard button should be hidden again");
        list.destroy();
    });

    QUnit.test('invisible attrs on fields are re-evaluated on field change', function (assert) {
        assert.expect(7);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="top">' +
                    '<field name="foo" attrs="{\'invisible\': [[\'bar\', \'=\', True]]}"/>' +
                    '<field name="bar"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('tbody td.o_invisible_modifier').length, 3,
            "there should be 3 invisible foo cells in readonly mode");

        // Make first line editable
        list.$('tbody tr:nth(0) td:nth(1)').click();

        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_invisible_modifier').length, 1,
            "the foo field widget should have been rendered as invisible");

        list.$('tbody tr:nth(0) td:nth(2) input').click();
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]:not(.o_invisible_modifier)').length, 1,
            "the foo field widget should have been marked as non-invisible");
        assert.strictEqual(list.$('tbody td.o_invisible_modifier').length, 2,
            "the foo field widget parent cell should not be invisible anymore");

        list.$('tbody tr:nth(0) td:nth(2) input').click();
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_invisible_modifier').length, 1,
            "the foo field widget should have been marked as invisible again");
        assert.strictEqual(list.$('tbody td.o_invisible_modifier').length, 3,
            "the foo field widget parent cell should now be invisible again");

        // Reswitch the cell to editable and save the row
        list.$('tbody tr:nth(0) td:nth(2) input').click();
        list.$('thead').click();

        assert.strictEqual(list.$('tbody td.o_invisible_modifier').length, 2,
            "there should be 2 invisible foo cells in readonly mode");

        list.destroy();
    });

    QUnit.test('readonly attrs on fields are re-evaluated on field change', function (assert) {
        assert.expect(9);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="top">' +
                    '<field name="foo" attrs="{\'readonly\': [[\'bar\', \'=\', True]]}"/>' +
                    '<field name="bar"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('tbody td.o_readonly_modifier').length, 3,
            "there should be 3 readonly foo cells in readonly mode");

        // Make first line editable
        list.$('tbody tr:nth(0) td:nth(1)').click();

        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > span[name="foo"]').length, 1,
            "the foo field widget should have been rendered as readonly");

        list.$('tbody tr:nth(0) td:nth(2) input').click();
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]').length, 1,
            "the foo field widget should have been rerendered as editable");
        assert.strictEqual(list.$('tbody td.o_readonly_modifier').length, 2,
            "the foo field widget parent cell should not be readonly anymore");

        list.$('tbody tr:nth(0) td:nth(2) input').click();
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > span[name="foo"]').length, 1,
            "the foo field widget should have been rerendered as readonly");
        assert.strictEqual(list.$('tbody td.o_readonly_modifier').length, 3,
            "the foo field widget parent cell should now be readonly again");

        list.$('tbody tr:nth(0) td:nth(2) input').click();
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]').length, 1,
            "the foo field widget should have been rerendered as editable again");
        assert.strictEqual(list.$('tbody td.o_readonly_modifier').length, 2,
            "the foo field widget parent cell should not be readonly again");

        // Click outside to leave edition mode
        list.$el.click();

        assert.strictEqual(list.$('tbody td.o_readonly_modifier').length, 2,
            "there should be 2 readonly foo cells in readonly mode");

        list.destroy();
    });

    QUnit.test('required attrs on fields are re-evaluated on field change', function (assert) {
        assert.expect(7);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="top">' +
                    '<field name="foo" attrs="{\'required\': [[\'bar\', \'=\', True]]}"/>' +
                    '<field name="bar"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('tbody td.o_required_modifier').length, 3,
            "there should be 3 required foo cells in readonly mode");

        // Make first line editable
        list.$('tbody tr:nth(0) td:nth(1)').click();

        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_required_modifier').length, 1,
            "the foo field widget should have been rendered as required");

        list.$('tbody tr:nth(0) td:nth(2) input').click();
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]:not(.o_required_modifier)').length, 1,
            "the foo field widget should have been marked as non-required");
        assert.strictEqual(list.$('tbody td.o_required_modifier').length, 2,
            "the foo field widget parent cell should not be required anymore");

        list.$('tbody tr:nth(0) td:nth(2) input').click();
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_required_modifier').length, 1,
            "the foo field widget should have been marked as required again");
        assert.strictEqual(list.$('tbody td.o_required_modifier').length, 3,
            "the foo field widget parent cell should now be required again");

        // Reswitch the cell to editable and save the row
        list.$('tbody tr:nth(0) td:nth(2) input').click();
        list.$('thead').click();

        assert.strictEqual(list.$('tbody td.o_required_modifier').length, 2,
            "there should be 2 required foo cells in readonly mode");

        list.destroy();
    });

    QUnit.test('leaving unvalid rows in edition', function (assert) {
        assert.expect(4);

        var warnings = 0;
        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="bottom">' +
                    '<field name="foo" required="1"/>' +
                    '<field name="bar"/>' +
                '</tree>',
            intercepts: {
                warning: function (ev) {
                    warnings++;
                },
            },
        });

        // Start first line edition
        var $firstFooTd = list.$('tbody tr:nth(0) td:nth(1)');
        $firstFooTd.click();

        // Remove required foo field value
        $firstFooTd.find('input').val("").trigger("input");

        // Try starting other line edition
        var $secondFooTd = list.$('tbody tr:nth(1) td:nth(1)');
        $secondFooTd.click();

        assert.strictEqual($firstFooTd.parent('.o_selected_row').length, 1,
            "first line should still be in edition as invalid");
        assert.strictEqual(list.$('tbody tr.o_selected_row').length, 1,
            "no other line should be in edition");
        assert.strictEqual($firstFooTd.find('input.o_field_invalid').length, 1,
            "the required field should be marked as invalid");
        assert.strictEqual(warnings, 1,
            "a warning should have been displayed");

        list.destroy();
    });

    QUnit.test('open a virtual id', function (assert) {
        assert.expect(1);

        var list = createView({
            View: ListView,
            model: 'event',
            data: this.data,
            arch: '<tree><field name="name"/></tree>',
        });

        testUtils.intercept(list, "switch_view", function (event) {
            assert.deepEqual(event.data, {
                    'model': 'event',
                    'res_id': '2-20170808020000',
                    'view_type': 'form',
                    'mode': 'readonly'
                },
                "should trigger switch to the form view for the record virtual id");
        });
        list.$('td:contains(virtual)').click();

        list.destroy();
    });

    QUnit.test('pressing enter on last line of editable list view', function (assert) {
        assert.expect(7);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
            mockRPC: function (route, args) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });

        // click on 3rd line
        list.$('td:contains(gnap)').click();
        assert.ok(list.$('tr.o_data_row:eq(2)').hasClass('o_selected_row'),
            "3rd row should be selected");

        // press enter in input
        list.$('tr.o_selected_row input').trigger({type: 'keydown', which: 13}); // enter
        assert.ok(list.$('tr.o_data_row:eq(3)').hasClass('o_selected_row'),
            "4rd row should be selected");
        assert.notOk(list.$('tr.o_data_row:eq(2)').hasClass('o_selected_row'),
            "3rd row should no longer be selected");

        // press enter on last row
        list.$('tr.o_selected_row input').trigger({type: 'keydown', which: 13}); // enter
        assert.strictEqual(list.$('tr.o_data_row').length, 5, "should have created a 5th row");

        assert.verifySteps(['/web/dataset/search_read', '/web/dataset/call_kw/foo/default_get']);
        list.destroy();
    });

    QUnit.test('pressing tab on last cell of editable list view', function (assert) {
        assert.expect(7);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });

        list.$('td:contains(blip)').last().click();
        assert.strictEqual(document.activeElement.name, "foo",
            "focus should be on an input with name = foo");

        list.$('tr.o_selected_row input[name="foo"]').trigger({type: 'keydown', which: 9}); // tab
        assert.strictEqual(document.activeElement.name, "int_field",
            "focus should be on an input with name = int_field");

        list.$('tr.o_selected_row input[name="int_field"]').trigger({type: 'keydown', which: 9}); // tab

        assert.ok(list.$('tr.o_data_row:eq(4)').hasClass('o_selected_row'),
            "5th row should be selected");
        assert.strictEqual(document.activeElement.name, "foo",
            "focus should be on an input with name = foo");

        assert.verifySteps(['/web/dataset/search_read', '/web/dataset/call_kw/foo/default_get']);
        list.destroy();
    });

    QUnit.test('navigation with tab and read completes after default_get', function (assert) {
        assert.expect(8);

        var defaultGetDef = $.Deferred();
        var readDef = $.Deferred();

        var list = createView({
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
                    return readDef.then(_.constant(result));
                }
                if (args.method === 'default_get') {
                    return defaultGetDef.then(_.constant(result));
                }
                return result;
            },
        });

        list.$('td:contains(-4)').last().click();

        list.$('tr.o_selected_row input[name="int_field"]').val('1234').trigger('input');
        list.$('tr.o_selected_row input[name="int_field"]').trigger({type: 'keydown', which: 9}); // tab

        defaultGetDef.resolve();
        assert.strictEqual(list.$('tbody tr.o_data_row').length, 4,
            "should have 4 data rows");
        readDef.resolve();
        assert.strictEqual(list.$('tbody tr.o_data_row').length, 5,
            "should have 5 data rows");
        assert.strictEqual(list.$('td:contains(1234)').length, 1,
            "should have a cell with new value");

        // we trigger a tab to move to the second cell in the current row. this
        // operation requires that this.currentRow is properly set in the
        // list editable renderer.
        list.$('tr.o_selected_row input[name="foo"]').trigger({type: 'keydown', which: 9}); // tab
        assert.ok(list.$('tr.o_data_row:eq(4)').hasClass('o_selected_row'),
            "5th row should be selected");

        assert.verifySteps(['write', 'read', 'default_get']);
        list.destroy();
    });

    QUnit.test('display toolbar', function (assert) {
        assert.expect(3);

        var list = createView({
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
                sidebar: true,
            },
        });

        var $dropdowns = $('.o_web_client .o_control_panel .btn-group .o_dropdown_toggler_btn');
        assert.strictEqual($dropdowns.length, 2,
            "there should be 2 dropdowns in the toolbar.");
        var $actions = $('.o_web_client .o_control_panel .btn-group .dropdown-menu')[1].children;
        assert.strictEqual($actions.length, 3,
            "there should be 3 actions");
        var $customAction = $('.o_web_client .o_control_panel .btn-group .dropdown-menu li a')[2];
        assert.strictEqual($customAction.text.trim(), 'Action event',
            "the custom action should have 'Action event' as name");

        list.destroy();
    });

    QUnit.test('edit list line after line deletion', function (assert) {
        assert.expect(5);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="int_field"/></tree>',
        });

        list.$('.o_data_row:nth(2) > td:not(.o_list_record_selector)').first().click();
        assert.ok(list.$('.o_data_row:nth(2)').is('.o_selected_row'),
            "third row should be in edition");
        list.$buttons.find('.o_list_button_discard').click();
        list.$buttons.find('.o_list_button_add').click();
        assert.ok(list.$('.o_data_row:nth(0)').is('.o_selected_row'),
            "first row should be in edition (creation)");
        list.$buttons.find('.o_list_button_discard').click();
        assert.strictEqual(list.$('.o_selected_row').length, 0,
            "no row should be selected");
        list.$('.o_data_row:nth(2) > td:not(.o_list_record_selector)').first().click();
        assert.ok(list.$('.o_data_row:nth(2)').is('.o_selected_row'),
            "third row should be in edition");
        assert.strictEqual(list.$('.o_selected_row').length, 1,
            "no other row should be selected");

        list.destroy();
    });

    QUnit.test('inputs are disabled when unselecting rows', function (assert) {
        assert.expect(1);

        var list = createView({
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
        });

        list.$('td:contains(gnap)').click();
        var $input = list.$('tr.o_selected_row input[name="foo"]');
        $input.val('lemon').trigger('input');
        $input.trigger({type: 'keydown', which: $.ui.keyCode.DOWN});
        list.destroy();
    });

    QUnit.test('navigation with tab and readonly field', function (assert) {
        // This test makes sure that if we have 2 cells in a row, the first in
        // edit mode, and the second one readonly, then if we press TAB when the
        // focus is on the first, then the focus skip the readonly cells and
        // directly goes to the next line instead.
        assert.expect(2);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
        });

        // click on first td and press TAB
        list.$('td:contains(yop)').last().click();
        list.$('tr.o_selected_row input[name="foo"]').trigger({type: 'keydown', which: $.ui.keyCode.TAB});

        assert.ok(list.$('tr.o_data_row:eq(1)').hasClass('o_selected_row'),
            "2nd row should be selected");

        // we do it again. This was broken because the this.currentRow variable
        // was not properly set, and the second TAB could cause a crash.
        list.$('tr.o_selected_row input[name="foo"]').trigger({type: 'keydown', which: $.ui.keyCode.TAB});
        assert.ok(list.$('tr.o_data_row:eq(2)').hasClass('o_selected_row'),
            "3rd row should be selected");

        list.destroy();
    });

    QUnit.test('navigation with tab on a list with create="0"', function (assert) {
        assert.expect(4);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom" create="0">' +
                        '<field name="display_name"/>' +
                    '</tree>',
        });

        assert.strictEqual(list.$('.o_data_row').length, 4,
            "the list should contain 4 rows");

        list.$('.o_data_row:nth(2) .o_data_cell:first').click();
        assert.ok(list.$('.o_data_row:nth(2)').hasClass('o_selected_row'),
            "third row should be in edition");

        // Press 'Tab' -> should go to next line
        list.$('.o_selected_row input').trigger({type: 'keydown', which: 9});
        assert.ok(list.$('.o_data_row:nth(3)').hasClass('o_selected_row'),
            "fourth row should be in edition");

        // Press 'Tab' -> should go back to first line as the create action isn't available
        list.$('.o_selected_row input').trigger({type: 'keydown', which: 9});
        assert.ok(list.$('.o_data_row:first').hasClass('o_selected_row'),
            "first row should be in edition");

        list.destroy();
    });


    QUnit.test('navigation with tab on a one2many list with create="0"', function (assert) {
        assert.expect(4);

        this.data.foo.records[0].o2m = [1, 2];
        var form = createView({
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form><sheet>' +
                    '<field name="o2m">' +
                        '<tree editable="bottom" create="0">' +
                            '<field name="display_name"/>' +
                        '</tree>' +
                    '</field>' +
                '</sheet></form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.strictEqual(form.$('.o_field_widget[name=o2m] .o_data_row').length, 2,
            "there should be two records in the many2many");

        form.$('.o_field_widget[name=o2m] .o_data_cell:first').click();
        assert.ok(form.$('.o_field_widget[name=o2m] .o_data_row:first').hasClass('o_selected_row'),
            "first row should be in edition");

        // Press 'Tab' -> should go to next line
        form.$('.o_field_widget[name=o2m] .o_selected_row input').trigger({type: 'keydown', which: 9});
        assert.ok(form.$('.o_field_widget[name=o2m] .o_data_row:nth(1)').hasClass('o_selected_row'),
            "second row should be in edition");

        // Press 'Tab' -> should go back to first line as the create action isn't available
        form.$('.o_field_widget[name=o2m] .o_selected_row input').trigger({type: 'keydown', which: 9});
        assert.ok(form.$('.o_field_widget[name=o2m] .o_data_row:first').hasClass('o_selected_row'),
            "first row should be in edition");

        form.destroy();
    });

    QUnit.test('edition, then navigation with tab (with a readonly field)', function (assert) {
        // This test makes sure that if we have 2 cells in a row, the first in
        // edit mode, and the second one readonly, then if we edit and press TAB,
        // (before debounce), the save operation is properly done (before
        // selecting the next row)
        assert.expect(4);

        var list = createView({
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
        list.$('td:contains(yop)').click();
        list.$('tr.o_selected_row input[name="foo"]').val('new value').trigger('input');
        list.$('tr.o_selected_row input[name="foo"]').trigger({type: 'keydown', which: $.ui.keyCode.TAB});

        assert.strictEqual(list.$('tbody tr:first td:contains(new value)').length, 1,
            "should have the new value visible in dom");
        assert.verifySteps(["write", "read"]);
        list.destroy();
    });

    QUnit.test('skip invisible fields when navigating list view with TAB', function (assert) {
        assert.expect(2);

        var list = createView({
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

        list.$('td:contains(gnap)').click();
        assert.strictEqual(list.$('input[name="foo"]')[0], document.activeElement,
            "foo should be focused");
        list.$('input[name="foo"]').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.strictEqual(list.$('input[name="int_field"]')[0], document.activeElement,
            "int_field should be focused");

        list.destroy();
    });

    QUnit.test('skip buttons when navigating list view with TAB (end)', function (assert) {
        assert.expect(2);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<button name="kikou" string="Kikou" type="object"/>' +
                '</tree>',
            res_id: 1,
        });

        list.$('tbody tr:eq(2) td:eq(1)').click();
        assert.strictEqual(list.$('tbody tr:eq(2) input[name="foo"]')[0], document.activeElement,
            "foo should be focused");
        list.$('tbody tr:eq(2) input[name="foo"]').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.strictEqual(list.$('tbody tr:eq(3) input[name="foo"]')[0], document.activeElement,
            "next line should be selected");

        list.destroy();
    });

    QUnit.test('skip buttons when navigating list view with TAB (middle)', function (assert) {
        assert.expect(2);

        var list = createView({
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

        list.$('tbody tr:eq(2) td:eq(2)').click();
        assert.strictEqual(list.$('tbody tr:eq(2) input[name="foo"]')[0], document.activeElement,
            "foo should be focused");
        list.$('tbody tr:eq(2) input[name="foo"]').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.strictEqual(list.$('tbody tr:eq(2) input[name="int_field"]')[0], document.activeElement,
            "int_field should be focused");

        list.destroy();
    });

    QUnit.test('navigation: moving down with keydown', function (assert) {
        assert.expect(2);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
        });

        list.$('td:contains(yop)').click();
        assert.ok(list.$('tr.o_data_row:eq(0)').hasClass('o_selected_row'),
            "1st row should be selected");
        list.$('tr.o_selected_row input[name="foo"]').trigger({type: 'keydown', which: $.ui.keyCode.DOWN});
        assert.ok(list.$('tr.o_data_row:eq(1)').hasClass('o_selected_row'),
            "2nd row should be selected");
        list.destroy();
    });

    QUnit.test('navigation: moving right with keydown from text field', function (assert) {
        assert.expect(6);

        this.data.foo.fields.foo.type = 'text';
        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                '</tree>',
        });

        list.$('td:contains(yop)').click();
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
        $(textarea).trigger({type: 'keydown', which: $.ui.keyCode.RIGHT});
        assert.strictEqual(document.activeElement, list.$('[name="bar"] input')[0],
            "next field (checkbox) should now be focused");
        list.destroy();
    });

    QUnit.test('navigation: moving left/right with keydown', function (assert) {
        assert.expect(8);

        this.data.foo.fields.foo.type = 'text';
        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch:
                '<tree editable="bottom">' +
                    '<field name="m2m" widget="many2many_tags"/>' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                    '<field name="m2o"/>' +
                    '<field name="qux"/>' +
                '</tree>',
        });

        list.$('td:contains(13)').click();
        var $m2m = list.$('[name="m2m"] input');
        var $foo = list.$('textarea[name="foo"]');
        var $bar = list.$('[name="bar"] input');
        var $m2o = list.$('[name="m2o"] input');
        var $qux = list.$('input[name="qux"]');

        assert.strictEqual(document.activeElement, $qux[0],
            "'qux' input should be focused");

        $qux[0].selectionEnd = 0; // Simulate browser keyboard left behavior (unselect)
        $qux.trigger({type: 'keydown', which: $.ui.keyCode.LEFT});
        assert.strictEqual(document.activeElement, $m2o[0],
            "'m2o' input should be focused");

        // forget unselecting and try leaving
        $m2o.trigger({type: 'keydown', which: $.ui.keyCode.LEFT});
        assert.strictEqual(document.activeElement, $m2o[0],
            "'m2o' input should still be focused");

        $m2o[0].selectionEnd = 0; // Simulate browser keyboard left behavior (unselect)
        $m2o.trigger({type: 'keydown', which: $.ui.keyCode.LEFT});
        assert.strictEqual(document.activeElement, $bar[0],
            "'bar' input should be focused");

        // no unselect here as it is a checkbox
        $bar.trigger({type: 'keydown', which: $.ui.keyCode.LEFT});
        assert.strictEqual(document.activeElement, $foo[0],
            "'foo' input should be focused");

        // forget unselecting and try leaving
        $foo.trigger({type: 'keydown', which: $.ui.keyCode.LEFT});
        assert.strictEqual(document.activeElement, $foo[0],
            "'foo' input should still be focused");

        $foo[0].selectionEnd = 0; // Simulate browser keyboard left behavior (unselect)
        $foo.trigger({type: 'keydown', which: $.ui.keyCode.LEFT});
        assert.strictEqual(document.activeElement, $m2m[0],
            "'m2m' input should be focused");

        $m2m[0].selectionStart = $m2m[0].value.length; // Simulate browser keyboard right behavior (unselect)
        $m2m.trigger({type: 'keydown', which: $.ui.keyCode.RIGHT});
        assert.strictEqual(document.activeElement, $foo[0],
            "'foo' input should be focused");

        list.destroy();
    });

    QUnit.test('discarding changes in a row properly updates the rendering', function (assert) {
        assert.expect(3);

        var list = createView({
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

        list.$('.o_data_cell:first').click();
        list.$('input[name="foo"]').val("hello").trigger('input');
        list.$buttons.find('.o_list_button_discard').click();
        assert.strictEqual($('.modal:visible').length, 1,
            "a modal to ask for discard should be visible");

        $('.modal:visible .btn-primary').click();
        assert.strictEqual(list.$('.o_data_cell:first').text(), "yop",
            "first cell should still contain 'yop'");

        list.destroy();
    });

    QUnit.test('numbers in list are right-aligned', function (assert) {
        assert.expect(2);

        var currencies = {};
        _.each(this.data.res_currency.records, function (currency) {
            currencies[currency.id] = currency;
        });
        var list = createView({
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

        list.$('.o_data_cell:first').click();

        var nbInputRight = _.filter(list.$('.o_data_row:first > .o_data_cell input'), function (el) {
            var style = window.getComputedStyle(el);
            return style.textAlign === 'right';
        }).length;
        assert.strictEqual(nbInputRight, 2,
            "there should be two right-aligned input");

        list.destroy();
    });

    QUnit.test('grouped list are not editable (ungrouped first)', function (assert) {
        // Editable grouped list views are not supported, so the purpose of this
        // test is to check that when a list view is grouped, its editable
        // attribute is ignored
        // In this test, the view isn't grouped at the beginning, so it is first
        // editable, and then it is reloaded with a groupBy and is no longer
        // editable
        assert.expect(5);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
            intercepts: {
                switch_view: function (event) {
                    var resID = event.data.res_id || false;
                    assert.step('switch view ' + event.data.view_type + ' ' + resID);
                },
            },
        });

        list.$('.o_data_cell:first').click();
        assert.verifySteps([], 'no switch view should have been requested');
        assert.strictEqual(list.$('.o_selected_row').length, 1,
            "a row should be in edition");

        // reload with groupBy
        list.reload({groupBy: ['bar']});

        // clicking on record should open the form view
        list.$('.o_group_header:first').click();
        list.$('.o_data_cell:first').click();

        // clicking on create button should open the form view
        list.$buttons.find('.o_list_button_add').click();
        assert.verifySteps(['switch view form 1', 'switch view form false'],
            'two switch view to form should have been requested');

        list.destroy();
    });

    QUnit.test('grouped list are not editable (grouped first)', function (assert) {
        // Editable grouped list views are not supported, so the purpose of this
        // test is to check that when a list view is grouped, its editable
        // attribute is ignored
        // In this test, the view is grouped at the beginning, so it isn't
        // editable, and then it is reloaded with no groupBy and becomes editable
        assert.expect(6);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/><field name="bar"/></tree>',
            intercepts: {
                switch_view: function (event) {
                    var resID = event.data.res_id || false;
                    assert.step('switch view ' + event.data.view_type + ' ' + resID);
                },
            },
            groupBy: ['bar'],
        });

        // the view being grouped, it is not editable, so clicking on a record
        // should open the form view
        list.$('.o_group_header:first').click(); // open first group
        list.$('.o_data_cell:first').click();

        // for the same reason, clicking on 'Create' should open the form view
        list.$buttons.find('.o_list_button_add').click();

        assert.verifySteps(['switch view form 1', 'switch view form false'],
            "two switch view to form should have been requested");

        // reload without groupBy
        list.reload({groupBy: []});

        // as the view is no longer grouped, it is editable, so clicking on a
        // row should switch it in edition
        list.$('.o_data_cell:first').click();

        assert.verifySteps(['switch view form 1', 'switch view form false'],
            "no more switch view should have been requested");
        assert.strictEqual(list.$('.o_selected_row').length, 1,
            "a row should be in edition");

        // clicking on the body should leave the edition
        $('body').click();
        assert.strictEqual(list.$('.o_selected_row').length, 0,
            "the row should no longer be in edition");

        list.destroy();
    });

    QUnit.test('field values are escaped', function (assert) {
        assert.expect(1);
        var value = '<script>throw Error();</script>';

        this.data.foo.records[0].foo = value;

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/></tree>',
        });

        assert.strictEqual(list.$('.o_data_cell:first').text(), value,
            "value should have been escaped");

        list.destroy();
    });

    QUnit.test('pressing ESC discard the current line changes', function (assert) {
        assert.expect(3);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo"/></tree>',
        });

        list.$buttons.find('.o_list_button_add').click();

        list.$('input[name="foo"]').trigger({type: 'keydown', which: $.ui.keyCode.ESCAPE});
        assert.strictEqual(list.$('tr.o_data_row').length, 4,
            "should have 4 data row in list");
        assert.strictEqual(list.$('tr.o_data_row.o_selected_row').length, 0,
            "no rows should be selected");
        assert.ok(!list.$buttons.find('.o_list_button_save').is(':visible'),
            "should not have a visible save button");
        list.destroy();
    });

    QUnit.test('pressing ESC discard the current line changes (with required)', function (assert) {
        assert.expect(3);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="foo" required="1"/></tree>',
        });

        list.$buttons.find('.o_list_button_add').click();

        list.$('input[name="foo"]').trigger({type: 'keydown', which: $.ui.keyCode.ESCAPE});
        assert.strictEqual(list.$('tr.o_data_row').length, 4,
            "should have 4 data row in list");
        assert.strictEqual(list.$('tr.o_data_row.o_selected_row').length, 0,
            "no rows should be selected");
        assert.ok(!list.$buttons.find('.o_list_button_save').is(':visible'),
            "should not have a visible save button");
        list.destroy();
    });

    QUnit.test('field with password attribute', function (assert) {
        assert.expect(2);

        var list = createView({
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

    QUnit.test('list with handle widget', function (assert) {
        assert.expect(11);

        var list = createView({
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
                    return $.when();
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
        testUtils.dragAndDrop(
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

    QUnit.test('result of consecutive resequences is correctly sorted', function (assert) {
        assert.expect(9);
        this.data = { // we want the data to be minimal to have a minimal test
            foo: {
                fields: {int_field: {string: "int_field", type: "integer", sortable: true}},
                records: [
                    {id: 1, int_field: 0},
                    {id: 2, int_field: 1},
                    {id: 3, int_field: 2},
                    {id: 4, int_field: 3},
                ]
            }
        };
        var moves = 0;
        var list = createView({
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
                            offset: 2,
                            field: "int_field",
                        });
                    }
                    if (moves === 1) {
                        assert.deepEqual(args, {
                            model: "foo",
                            ids: [1, 4, 2, 3],
                            field: "int_field",
                        });
                    }
                    if (moves === 2) {
                        assert.deepEqual(args, {
                            model: "foo",
                            ids: [2, 4],
                            offset: 1,
                            field: "int_field",
                        });
                    }
                    if (moves === 3) {
                        assert.deepEqual(args, {
                            model: "foo",
                            ids: [1, 4, 2, 3],
                            field: "int_field",
                        });
                    }
                    moves += 1;
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.strictEqual(list.$('tbody tr td').text(), '1234',
            "default should be sorted by id");
        testUtils.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').eq(2),
            {position: 'top'}
        );
        assert.strictEqual(list.$('tbody tr td').text(), '1243',
            "the int_field (sequence) should have been correctly updated");
        testUtils.dragAndDrop(
            list.$('.ui-sortable-handle').eq(2),
            list.$('tbody tr').eq(1),
            {position: 'top'}
        );
        assert.deepEqual(list.$('tbody tr td').text(), '1423',
            "the int_field (sequence) should have been correctly updated");
        testUtils.dragAndDrop(
            list.$('.ui-sortable-handle').eq(1),
            list.$('tbody tr').eq(3),
            {position: 'top'}
        );
        assert.deepEqual(list.$('tbody tr td').text(), '1243',
            "the int_field (sequence) should have been correctly updated");
        testUtils.dragAndDrop(
            list.$('.ui-sortable-handle').eq(2),
            list.$('tbody tr').eq(1),
            {position: 'top'}
        );
        assert.deepEqual(list.$('tbody tr td').text(), '1423',
            "the int_field (sequence) should have been correctly updated");
        list.destroy();
    });

    QUnit.test('editable list with handle widget', function (assert) {
        assert.expect(12);

        // resequence makes sense on a sequence field, not on arbitrary fields
        this.data.foo.records[0].int_field = 0;
        this.data.foo.records[1].int_field = 1;
        this.data.foo.records[2].int_field = 2;
        this.data.foo.records[3].int_field = 3;

        var list = createView({
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
                    return $.when();
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
        testUtils.dragAndDrop(
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

        list.$('tbody tr:eq(1) td:last').click();

        assert.strictEqual(list.$('tbody tr:eq(1) td:last input').val(), '0',
            "the edited record should be the good one");

        list.destroy();
    });

    QUnit.test('editable list with handle widget with slow network', function (assert) {
        assert.expect(15);

        // resequence makes sense on a sequence field, not on arbitrary fields
        this.data.foo.records[0].int_field = 0;
        this.data.foo.records[1].int_field = 1;
        this.data.foo.records[2].int_field = 2;
        this.data.foo.records[3].int_field = 3;

        var def = $.Deferred();

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top">' +
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
                    return $.when(def);
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
        testUtils.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        // edit moved row before the end of resequence
        list.$('tbody tr:eq(3) td:last').click();

        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').length, 0,
            "shouldn't edit the line before resequence");

        def.resolve();

        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').length, 1,
            "should edit the line after resequence");

        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').val(), '300',
            "fourth record should have amount 300");

        list.$('tbody tr:eq(3) td:last input').val(301).trigger('input');
        list.$('tbody tr:eq(0) td:last').click();

        list.$buttons.find('.o_list_button_save').click();

        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '0',
            "second record should have amount 1");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '500',
            "third record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '301',
            "fourth record should have amount 301");

        list.$('tbody tr:eq(3) td:last').click();
        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').val(), '301',
            "fourth record should have amount 301");

        list.destroy();
    });

    QUnit.test('multiple clicks on Add do not create invalid rows', function (assert) {
        assert.expect(2);

        this.data.foo.onchanges = {
            m2o: function () {},
        };

        var def = $.Deferred();
        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="m2o" required="1"/></tree>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'onchange') {
                    return $.when(def).then(_.constant(result));
                }
                return result;
            },
        });

        assert.strictEqual(list.$('.o_data_row').length, 4,
            "should contain 4 records");

        // click on Add twice, and delay the onchange
        list.$buttons.find('.o_list_button_add').click();
        list.$buttons.find('.o_list_button_add').click();

        def.resolve();

        assert.strictEqual(list.$('.o_data_row').length, 5,
            "only one record should have been created");

        list.destroy();
    });

    QUnit.test('reference field rendering', function (assert) {
        assert.expect(4);

        this.data.foo.records.push({
            id: 5,
            reference: 'res_currency,2',
        });

        var list = createView({
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
        assert.strictEqual(list.$('tbody td').text(), "Value 1USDEUREUR",
            "should have the display_name of the reference");
        list.destroy();
    });

    QUnit.test('editable list view: contexts are correctly sent', function (assert) {
        assert.expect(6);

        var list = createView({
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

        list.$('.o_data_cell:first').click();
        list.$('.o_field_widget[name=foo]').val('abc').trigger('input');
        list.$buttons.find('.o_list_button_save').click();

        list.destroy();
    });

    QUnit.test('list grouped by date:month', function (assert) {
        assert.expect(1);

        var list = createView({
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

    QUnit.test('grouped list edition with toggle_button widget', function (assert) {
        assert.expect(3);

        var list = createView({
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

        list.$('.o_group_header:first').click(); // open the first group
        assert.strictEqual(list.$('.o_data_row:first .o_toggle_button_success').length, 1,
            "boolean value of the first record should be true");
        list.$('.o_data_row:first .o_icon_button').click(); // toggle the value
        assert.strictEqual(list.$('.o_data_row:first .text-muted:not(.o_toggle_button_success)').length, 1,
            "boolean button should have been updated");

        list.destroy();
    });

    QUnit.test('grouped list view, indentation for empty group', function (assert) {
        assert.expect(3);

        this.data.foo.fields.priority = {
            string: "Priority",
            type: "selection",
            selection: [[1, "Low"], [2, "Medium"], [3, "High"]],
            default: 1,
        };
        this.data.foo.records.push({id: 5, foo: "blip", int_field: -7, m2o: 1, priority: 2});
        this.data.foo.records.push({id: 6, foo: "blip", int_field: 5, m2o: 1, priority: 3});

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="id"/></tree>',
            groupBy: ['priority', 'm2o'],
            mockRPC: function (route, args) {
                // Override of the read_group to display the row even if there is no record in it,
                // to mock the behavihour of some fields e.g stage_id on the sale order.
                if (args.method === 'read_group' && args.kwargs.groupby[0] === "m2o") {
                    return $.when([
                        {
                            id: 8,
                            m2o:[1,"Value 1"],
                            m2o_count: 0
                        }, {
                            id: 2,
                            m2o:[2,"Value 2"],
                            m2o_count: 1
                        }
                    ]);
                }
                return this._super.apply(this, arguments);
            },
        });

        // open the first group
        list.$('.o_group_header:first').click();
        assert.strictEqual(list.$('th.o_group_name').eq(1).children().length, 1,
            "There should be an empty element creating the indentation for the subgroup.");
        assert.strictEqual(list.$('th.o_group_name').eq(1).children().eq(0).hasClass('fa'), true,
            "The first element of the row name should have the fa class");
        assert.strictEqual(list.$('th.o_group_name').eq(1).children().eq(0).is('span'), true,
            "The first element of the row name should be a span");
        list.destroy();
    });

    QUnit.test('basic support for widgets', function (assert) {
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

        var list = createView({
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

    QUnit.test('use the limit attribute in arch', function (assert) {
        assert.expect(3);

        var list = createView({
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

        assert.strictEqual(list.$('.o_data_row').length, 2,
            'should display 2 data rows');
        list.destroy();
    });

    QUnit.test('check if the view destroys all widgets and instances', function (assert) {
        assert.expect(1);

        var instanceNumber = 0;
        testUtils.patch(mixins.ParentedMixin, {
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

        var list = createView(params);
        list.destroy();

        var initialInstanceNumber = instanceNumber;
        instanceNumber = 0;

        list = createView(params);

        // call destroy function of controller to ensure that it correctly destroys everything
        list.__destroy();

        assert.strictEqual(instanceNumber, initialInstanceNumber+1, "every widget must be destroyed exept the parent");

        list.destroy();

        testUtils.unpatch(mixins.ParentedMixin);
    });

    QUnit.test('concurrent reloads finishing in inverse order', function (assert) {
        assert.expect(3);

        var blockSearchRead = false;
        var def = $.Deferred();
        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/></tree>',
            mockRPC: function (route) {
                var result = this._super.apply(this, arguments);
                if (route === '/web/dataset/search_read' && blockSearchRead) {
                    return $.when(def).then(_.constant(result));
                }
                return result;
            },
        });

        assert.strictEqual(list.$('.o_list_view .o_data_row').length, 4,
            "list view should contain 4 records");

        // reload with a domain (this request is blocked)
        blockSearchRead = true;
        list.reload({domain: [['foo', '=', 'yop']]});

        assert.strictEqual(list.$('.o_list_view .o_data_row').length, 4,
            "list view should still contain 4 records (search_read being blocked)");

        // reload without the domain
        blockSearchRead = false;
        list.reload({domain: []});

        // unblock the RPC
        def.resolve();
        assert.strictEqual(list.$('.o_list_view .o_data_row').length, 4,
            "list view should still contain 4 records");

        list.destroy();
    });
});

});
