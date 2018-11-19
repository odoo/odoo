odoo.define('web.list_tests', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var config = require('web.config');
var core = require('web.core');
var basicFields = require('web.basic_fields');
var FormView = require('web.FormView');
var ListView = require('web.ListView');
var mixins = require('web.mixins');
var NotificationService = require('web.NotificationService');
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
                    int_field: {string: "int_field", type: "integer", sortable: true, group_operator: "sum"},
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

        assert.hasClass(list.$el,'o_cannot_create',
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
            viewOptions: {hasSidebar: true},
            arch: '<tree delete="0"><field name="foo"/></tree>',
        });

        assert.isNotVisible(list.sidebar.$el, 'sidebar should be invisible');
        assert.ok(list.$('tbody td.o_list_record_selector').length, 'should have at least one record');

        testUtils.dom.click(list.$('tbody td.o_list_record_selector:first input'));
        assert.isVisible(list.sidebar.$el, 'sidebar should be visible');
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

        assert.containsN(list, 'th', 3, "should have 2 th");
        assert.containsN(list, 'th', 3, "should have 3 th");
        assert.strictEqual(list.$('td:contains(yop)').length, 1, "should contain yop");

        assert.ok(list.$buttons.find('.o_list_button_add').is(':visible'),
            "should have a visible Create button");
        assert.ok(!list.$buttons.find('.o_list_button_save').is(':visible'),
            "should not have a visible save button");
        assert.ok(!list.$buttons.find('.o_list_button_discard').is(':visible'),
            "should not have a visible discard button");

        testUtils.dom.click(list.$('td:not(.o_list_record_selector)').first());

        assert.ok(!list.$buttons.find('.o_list_button_add').is(':visible'),
            "should not have a visible Create button");
        assert.ok(list.$buttons.find('.o_list_button_save').is(':visible'),
            "should have a visible save button");
        assert.ok(list.$buttons.find('.o_list_button_discard').is(':visible'),
            "should have a visible discard button");

        testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

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
        assert.containsN(list, 'th', 2, "should have 2 th");
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

        assert.containsN(list, 'tbody tr:first td', 4,
            "there should be 4 cells in the first row");
        assert.containsOnce(list, 'tbody td.o_invisible_modifier',
            "there should be 1 invisible bar cell");
        assert.hasClass(list.$('tbody tr:first td:eq(2)'),'o_invisible_modifier',
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
            mockRPC: function (route) {
                assert.step(_.last(route.split('/')));
                return this._super.apply(this, arguments);
            },
        });

        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
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

        assert.containsN(list, 'tbody tr', 4, "should have 4 rows");
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
        assert.containsN(list, 'tr.o_group_header', 2, "should have 2 .o_group_header");
        assert.containsN(list, 'th.o_group_name', 2, "should have 2 .o_group_name");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 1 col without selector', function (assert) {
        assert.expect(1);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/></tree>',
            groupBy: ['bar'],
            hasSelectors: false,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 1,
        "group header should have exactly 1 column");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 1 col with selector', function (assert) {
        assert.expect(1);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/></tree>',
            groupBy: ['bar'],
            hasSelectors: true,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 1,
            "group header should have exactly 1 column");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 2 col without selector', function (assert) {
        assert.expect(1);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
            hasSelectors: false,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 2,
            "group header should have exactly 2 column");
        list.destroy();
    });

    QUnit.test('basic grouped list rendering 2 col with selector', function (assert) {
        assert.expect(1);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree ><field name="foo"/><field name="bar"/></tree>',
            groupBy: ['bar'],
            hasSelectors: true,
        });

        assert.strictEqual(list.$('.o_group_header:first').children().length, 2,
        "group header should have exactly 2 column");
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

        testUtils.dom.click(list.$('th.o_group_name:nth(1)'));
        assert.strictEqual(list.$('tbody:eq(1) tr').length, 2, "open group should contain 2 records");
        assert.containsN(list, 'tbody', 3, "should contain 3 tbody");
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

        testUtils.mock.intercept(list, "open_record", function () {
            assert.ok("list view should trigger 'open_record' event");
        });

        testUtils.dom.click(list.$('tr td:not(.o_list_record_selector)').first());
        list.update({groupBy: ['foo']});
        assert.containsN(list, 'tr.o_group_header', 3, "list should be grouped");
        testUtils.dom.click(list.$('th.o_group_name').first());

        testUtils.dom.click(list.$('tr:not(.o_group_header) td:not(.o_list_record_selector)').first());
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
        testUtils.dom.click($td);
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

    QUnit.test('editable list view: line with no active element', function (assert) {
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

        var form = createView({
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
        testUtils.dom.click($td);
        testUtils.dom.click($td2.find('.o_boolean_toggle input'));

        testUtils.form.clickSave(form);

        form.destroy();
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
        assert.doesNotHaveClass($td.parent(), 'o_selected_row', "td should not be in edit mode");
        testUtils.dom.click($td);
        assert.hasClass($td.parent(),'o_selected_row', "td should be in edit mode");
        list.destroy();
    });

    QUnit.test('editable list: add a line and discard', function (assert) {
        assert.expect(11);

        testUtils.mock.patch(basicFields.FieldChar, {
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

        assert.containsN(list, 'tbody tr', 4,
            "list should contain 4 rows");
        assert.containsOnce(list, '.o_data_row',
            "list should contain one record (and thus 3 empty rows)");
        assert.strictEqual(list.pager.$('.o_pager_value').text(), '1-1',
            "pager should be correct");

        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.containsN(list, 'tbody tr', 4,
            "list should still contain 4 rows");
        assert.containsN(list, '.o_data_row', 2,
            "list should contain two record (and thus 2 empty rows)");
        assert.strictEqual(list.pager.$('.o_pager_value').text(), '1-2',
            "pager should be correct");

        testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));

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
        testUtils.mock.intercept(list, "field_changed", function () {
            n += 1;
        });
        testUtils.dom.click($td);
        testUtils.fields.editInput($td.find('input'), 'abc');
        assert.strictEqual(n, 1, "field_changed should have been triggered");
        testUtils.dom.click(list.$('td:not(.o_list_record_selector)').eq(2));
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
        testUtils.dom.click($td);
        testUtils.fields.editInput($td.find('input'), 'abc');
        assert.strictEqual($td.find('input').val(), 'abc', "char field has been edited correctly");

        var $next_row_td = list.$('tbody tr:eq(1) td:not(.o_list_record_selector)').first();
        testUtils.dom.click($next_row_td);
        assert.strictEqual(list.$('td:not(.o_list_record_selector)').first().text(), 'abc',
            'changes should be saved correctly');
        assert.doesNotHaveClass(list.$('tbody tr').first(), 'o_selected_row',
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

        testUtils.dom.click(list.$('.o_data_cell:first'));
        testUtils.fields.editInput(list.$('input[name="foo"]'), 'xyz');
        testUtils.dom.click(list.$('.o_column_sortable'));

        assert.hasClass(list.$('.o_data_row:first'),'o_selected_row',
            "first row should still be in edition");

        testUtils.dom.click(list.$buttons.find('.o_list_button_save'));
        assert.doesNotHaveClass(list.$buttons, 'o-editing',
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
        testUtils.dom.click($firstRowSelector);
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
        assert.expect(6);

        var list = createView({
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
        testUtils.dom.click(list.$('.o_group_header:contains("blip (2)")'));
        testUtils.dom.click(list.$('.o_data_row:first input'));
        assert.isVisible(list.sidebar);

        // open yop grouping and verify blip are still checked
        testUtils.dom.click(list.$('.o_group_header:contains("yop (1)")'));
        assert.containsOnce(list, '.o_data_row input:checked',
            "opening a grouping does not uncheck others");
        assert.isVisible(list.sidebar);

        // close and open blip grouping and verify blip are unchecked
        testUtils.dom.click(list.$('.o_group_header:contains("blip (2)")'));
        testUtils.dom.click(list.$('.o_group_header:contains("blip (2)")'));
        assert.containsNone(list, '.o_data_row input:checked',
            "opening and closing a grouping uncheck its elements");
        assert.isNotVisible(list.sidebar);

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

        testUtils.dom.click($tbody_selectors.first());
        testUtils.dom.click($tbody_selectors.last());
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "6",
                        "total should be 6 as first and last records are selected");

        testUtils.dom.click($thead_selector);
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

        testUtils.dom.click($groupHeader1);
        testUtils.dom.click(list.$('tbody .o_list_record_selector input').first());
        assert.strictEqual(list.$('tfoot td:last()').text(), "10",
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

        testUtils.dom.click(list.$('tr.o_data_row td.o_data_cell').first());
        testUtils.fields.editInput(list.$('td.o_data_cell input'), "15");

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
            arch: '<tree editable="bottom"><field name="foo" /><field name="int_field" sum="Sum"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.step(args.kwargs.orderby || 'default order');
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(list.$('tbody .o_list_number').text(), '10517',
            "initial order should be 10, 5, 17");
        assert.strictEqual(list.$('tfoot td:last()').text(), '32', "total should be 32");

        testUtils.dom.click(list.$('.o_column_sortable'));
        assert.strictEqual(list.$('tfoot td:last()').text(), '32', "total should still be 32");
        assert.strictEqual(list.$('tbody .o_list_number').text(), '51017',
            "order should be 5, 10, 17");

        testUtils.dom.click(list.$('.o_column_sortable'));
        assert.strictEqual(list.$('tbody .o_list_number').text(), '17105',
            "initial order should be 17, 10, 5");
        assert.strictEqual(list.$('tfoot td:last()').text(), '32', "total should still be 32");

        assert.verifySteps(['default order', 'int_field ASC', 'int_field DESC']);

        list.destroy();
    });

    QUnit.test('groups cannot be sorted on non-aggregable fields', function (assert) {
        assert.expect(6);
        this.data.foo.fields.sort_field = {string: "sortable_field", type: "sting", sortable: true, default: "value"};
        _.each(this.data.records, function(elem) {
            elem.sort_field = "value" + elem.id;
        });
        this.data.foo.fields.foo.sortable= true;
        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            groupBy: ['foo'],
            arch: '<tree editable="bottom"><field name="foo" /><field name="int_field"/><field name="sort_field"/></tree>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.step(args.kwargs.orderby || 'default order');
                }
                return this._super.apply(this, arguments);
            },
        });
        //we cannot sort by sort_field since it doesn't have a group_operator
        testUtils.dom.click(list.$('.o_column_sortable:eq(2)'));
        //we can sort by int_field since it has a group_operator
        testUtils.dom.click(list.$('.o_column_sortable:eq(1)'));
        //we keep previous order
        testUtils.dom.click(list.$('.o_column_sortable:eq(2)'));
        //we can sort on foo since we are groupped by foo + previous order
        testUtils.dom.click(list.$('.o_column_sortable:eq(0)'));

        assert.verifySteps([
            'default order',
            'default order',
            'int_field ASC',
            'int_field ASC',
            'foo ASC, int_field ASC'
        ]);

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

        testUtils.dom.click($foo_td);
        testUtils.fields.editInput($foo_td.find('input'), 'tralala');

        assert.strictEqual($int_field_td.find('input').val(), "1007",
                        "should contain input with onchange applied");
        list.destroy();
    });

    QUnit.test('column width should not change when switching mode', function (assert) {
        assert.expect(4);

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
        var startWidth = list.$('table').addBack('table').width();

        // start edition of first row
        testUtils.dom.click(list.$('td:not(.o_list_record_selector)').first());

        var editionWidths = _.pluck(list.$('thead th'), 'offsetWidth');
        var editionWidth = list.$('table').addBack('table').width();

        // leave edition
        testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

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

    QUnit.test('deleting one record', function (assert) {
        assert.expect(5);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {hasSidebar: true},
            arch: '<tree><field name="foo"/></tree>',
        });

        assert.isNotVisible(list.sidebar.$el, 'sidebar should be invisible');
        assert.containsN(list, 'tbody td.o_list_record_selector', 4, "should have 4 records");

        testUtils.dom.click(list.$('tbody td.o_list_record_selector:first input'));

        assert.isVisible(list.sidebar.$el, 'sidebar should be visible');

        testUtils.dom.click(list.sidebar.$('.o_dropdown_toggler_btn:contains(Action)'));
        testUtils.dom.click(list.sidebar.$('a:contains(Delete)'));
        assert.hasClass($('body'),'modal-open', 'body should have modal-open clsss');

        testUtils.dom.click($('body .modal button span:contains(Ok)'));

        assert.containsN(list, 'tbody td.o_list_record_selector', 3, "should have 3 records");
        list.destroy();
    });

    QUnit.test('archiving one record', function (assert) {
        assert.expect(12);

        // add active field on foo model and make all records active
        this.data.foo.fields.active = {string: 'Active', type: 'boolean', default: true};

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            viewOptions: {hasSidebar: true},
            arch: '<tree><field name="foo"/></tree>',
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });

        assert.isNotVisible(list.sidebar.$el, 'sidebar should be invisible');
        assert.containsN(list, 'tbody td.o_list_record_selector', 4, "should have 4 records");

        testUtils.dom.click(list.$('tbody td.o_list_record_selector:first input'));

        assert.isVisible(list.sidebar.$el, 'sidebar should be visible');

        assert.verifySteps(['/web/dataset/search_read']);
        testUtils.dom.click(list.sidebar.$('.o_dropdown_toggler_btn:contains(Action)'));
        testUtils.dom.click(list.sidebar.$('a:contains(Archive)'));
        assert.strictEqual($('.modal').length, 1, 'a confirm modal should be displayed');
        testUtils.dom.click($('.modal-footer .btn-secondary'));
        assert.containsN(list, 'tbody td.o_list_record_selector', 4, "still should have 4 records");

        testUtils.dom.click(list.sidebar.$('.o_dropdown_toggler_btn:contains(Action)'));
        testUtils.dom.click(list.sidebar.$('a:contains(Archive)'));
        assert.strictEqual($('.modal').length, 1, 'a confirm modal should be displayed');
        testUtils.dom.click($('.modal-footer .btn-primary'));
        assert.containsN(list, 'tbody td.o_list_record_selector', 3, "should have 3 records");
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

        assert.isVisible(list.pager.$el, "pager should be visible");
        assert.strictEqual(list.pager.state.size, 4, "pager's size should be 4");
        list.update({ groupBy: ['bar']});
        assert.isNotVisible(list.pager.$el, "pager should be invisible");
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
        testUtils.dom.click(list.$('thead th:contains(Foo)'));
        assert.strictEqual(nbSearchRead, 1, "should have done one search_read");
        assert.ok(list.$('tbody tr:first td:contains(blip)').length,
            "record 3 should be first");
        assert.ok(list.$('tbody tr:eq(3) td:contains(yop)').length,
            "record 1 should be first");

        nbSearchRead = 0;
        testUtils.dom.click(list.$('thead th:contains(Foo)'));
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

        testUtils.form.clickEdit(form);
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");

        var $o2m = form.$('.o_field_widget[name=o2m]');
        testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        testUtils.fields.editInput($o2m.find('.o_field_widget'), "Value 2");
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");
        assert.ok(form.$('tbody tr:eq(2) td input').val(),
            "Value 2 should be third (shouldn't be sorted)");

        testUtils.form.clickSave(form);
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

        testUtils.form.clickEdit(form);
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");

        var $o2m = form.$('.o_field_widget[name=o2m]');
        testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
        testUtils.fields.editInput($o2m.find('.o_field_widget'), "Value 2");
        assert.ok(form.$('tbody tr:first td:contains(Value 1)').length,
            "Value 1 should be first");
        assert.ok(form.$('tbody tr:eq(1) td:contains(Value 3)').length,
            "Value 3 should be second");
        assert.ok(form.$('tbody tr:eq(2) td input').val(),
            "Value 2 should be third (shouldn't be sorted)");

        testUtils.dom.click(form.$('.o_form_sheet_bg'));

        testUtils.dom.click($o2m.find('.o_column_sortable'));
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 1',
            "Value 1 should be first");
        assert.strictEqual(form.$('tbody tr:eq(1)').text(), 'Value 2',
            "Value 2 should be second (should be sorted after saving)");
        assert.strictEqual(form.$('tbody tr:eq(2)').text(), 'Value 3',
            "Value 3 should be third");

        testUtils.dom.click($o2m.find('.o_column_sortable'));
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
        testUtils.dom.click(form.$('.o_pager_next'));
        assert.strictEqual(form.$('tbody tr:first').text(), 'Value 44',
            "record 44 should be first");
        assert.strictEqual(form.$('tbody tr:eq(4)').text(), 'Value 48',
            "record 48 should be last");

        testUtils.dom.click(form.$('.o_column_sortable'));
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
        assert.containsN(list, 'tbody button[name=notafield]', 4);
        assert.containsN(list, 'tbody button[name=notafield].o_yeah', 4, "class o_yeah should be set on the four button");
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

        assert.containsN(list, 'tbody tr.text-info', 3,
            "should have 3 columns with text-info class");

        assert.containsN(list, 'tbody tr', 4, "should have 4 rows");
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

        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.containsNone(list, 'tr.o_data_row.text-danger',
            "the data row should not have .text-danger decoration (int_field is unset)");
        testUtils.fields.editInput(list.$('input[name="int_field"]'), '-3');
        assert.containsOnce(list, 'tr.o_data_row.text-danger',
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

        assert.containsOnce(list, 'tbody tr.text-info',
            "should have 1 columns with text-info class with good datetime");

        assert.containsNone(list, 'tbody tr.text-danger',
            "should have 0 columns with text-danger class with wrong timezone datetime");

        assert.containsN(list, 'tbody tr', 4, "should have 4 rows");
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

        assert.containsOnce(list, '.o_view_nocontent',
            "should display the no content helper");

        assert.containsNone(list, 'table', "should not have a table in the dom");

        assert.strictEqual(list.$('.o_view_nocontent p.hello:contains(add a partner)').length, 1,
            "should have rendered no content helper from action");

        this.data.foo.records = records;
        list.reload();

        assert.containsNone(list, '.o_view_nocontent',
            "should not display the no content helper");
        assert.containsOnce(list, 'table', "should have a table in the dom");
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

        assert.containsNone(list, '.o_view_nocontent',
            "should not display the no content helper");

        assert.containsNone(list, 'tr.o_data_row',
            "should not have any data row");

        assert.containsOnce(list, 'table', "should have a table in the dom");
        list.destroy();
    });

    QUnit.test('list view, editable, without data', function (assert) {
        assert.expect(13);

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

        assert.containsOnce(list, '.o_view_nocontent',
            "should have a no content helper displayed");

        assert.containsNone(list, 'div.table-responsive',
            "should not have a div.table-responsive");
        assert.containsNone(list, 'table', "should not have rendered a table");

        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.containsNone(list, '.o_view_nocontent',
            "should not have a no content helper displayed");
        assert.containsOnce(list, 'table', "should have rendered a table");
        assert.strictEqual(list.$el.css('height'), list.$('div.table-responsive').css('height'),
            "the div for the table should take the full height");


        assert.hasClass(list.$('tbody tr:eq(0)'),'o_selected_row',
            "the date field td should be in edit mode");
        assert.strictEqual(list.$('tbody tr:eq(0) td:eq(1)').text().trim(), "",
            "the date field td should not have any content");

        assert.strictEqual(list.$('tr.o_selected_row .o_list_record_selector input').prop('disabled'), true,
            "record selector checkbox should be disabled while the record is not yet created");
        assert.strictEqual(list.$('.o_list_button button').prop('disabled'), true,
            "buttons should be disabled while the record is not yet created");

        testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        assert.strictEqual(list.$('tbody tr:eq(0) .o_list_record_selector input').prop('disabled'), false,
            "record selector checkbox should not be disabled once the record is created");
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

        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.containsOnce(list, 'table button.o_icon_button i.fa-phone',
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

        testUtils.dom.click(list.$('tbody td:not(.o_list_record_selector):first'));
        assert.strictEqual(list.$('td:not(.o_list_record_selector) input').length, 1, "first cell should be editable");

        assert.ok(list.$buttons.find('.o_list_button_discard').is(':visible'),
            "discard button should be visible");

        testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));

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

        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        testUtils.dom.click(list.$('div.table-responsive'));

        assert.strictEqual(createCount, 1, "should have created a record");

        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        testUtils.dom.click(list.$('tfoot'));

        assert.strictEqual(createCount, 2, "should have created a record");

        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        testUtils.dom.click(list.$('tbody tr').last());

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

        assert.containsN(list, '.o_list_button', 4,
            "there should be one button per row");
        assert.containsOnce(list, '.o_list_button:first .o_icon_button .fa.fa-car',
            'buttons should have correct icon');

        testUtils.dom.click(list.$('.o_list_button:first > button'));
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
        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2)'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(4) input.o_invisible_modifier').length, 1,
            "td that contains an invisible field should not be empty in edition");
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > button.o_invisible_modifier').length, 1,
            "td that contains an invisible button should not be empty in edition");
        testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));

        // click on the invisible field's cell to edit first row
        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(4)'));
        assert.hasClass(list.$('tbody tr:nth(0)'),'o_selected_row',
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

        assert.containsN(list, 'tbody tr:first td', 3,
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
        assert.expect(9);

        this.data.foo.fields.foo.readonly = true;

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field"/></tree>',
        });

        assert.hasClass(list.$('.o_data_row:first td:nth(1)'),'o_readonly_modifier',
            "foo field cells should have class 'o_readonly_modifier'");

        // edit the first row
        testUtils.dom.click(list.$('.o_data_row:first td:nth(1)'));
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
        testUtils.dom.click(list.$('.o_data_row:first td:nth(1)'));
        assert.hasClass(list.$('.o_data_row:first'),'o_selected_row',
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
                    assert.deepEqual(event.data.env.ids, envIDs,
                        "should notify the environment with the correct ids");
                },
            },
        });

        assert.strictEqual(nbRPCs.readGroup, 1, "should have done one read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");

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
        testUtils.dom.click(list.$('.o_group_header:first'));
        assert.strictEqual(nbRPCs.readGroup, 1, "should have done one read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");

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
        testUtils.dom.click($openGroup.find('.o_group_header:nth(2)'));
        assert.strictEqual(nbRPCs.readGroup, 0, "should have done no read_group");
        assert.strictEqual(nbRPCs.searchRead, 1, "should have done one search_read");

        var $openSubGroup = list.$('tbody:nth(2)');
        assert.containsN(list, 'tbody', 4, "there should be 4 tbodys");
        assert.strictEqual($openSubGroup.find('.o_data_row').length, 2,
            "open subgroup should contain 2 data rows");
        assert.strictEqual($openSubGroup.find('.o_data_row:first td:last').text(), '-4',
            "first record in open subgroup should be res_id 4 (with int_field -4)");

        // open a record (should trigger event 'open_record')
        testUtils.dom.click($openSubGroup.find('.o_data_row:first'));

        // sort by int_field (ASC) and check that open groups are still open
        nbRPCs = {readGroup: 0, searchRead: 0};
        envIDs = [5, 4]; // order of the records changed
        testUtils.dom.click(list.$('thead th:last'));
        assert.strictEqual(nbRPCs.readGroup, 2, "should have done two read_groups");
        assert.strictEqual(nbRPCs.searchRead, 1, "should have done one search_read");

        $openSubGroup = list.$('tbody:nth(2)');
        assert.containsN(list, 'tbody', 4, "there should be 4 tbodys");
        assert.strictEqual($openSubGroup.find('.o_data_row').length, 2,
            "open subgroup should contain 2 data rows");
        assert.strictEqual($openSubGroup.find('.o_data_row:first td:last').text(), '-7',
            "first record in open subgroup should be res_id 5 (with int_field -7)");

        // close first level group
        nbRPCs = {readGroup: 0, searchRead: 0};
        envIDs = []; // the group being closed, there is no more record in the environment
        testUtils.dom.click(list.$('.o_group_header:nth(1)'));
        assert.strictEqual(nbRPCs.readGroup, 0, "should have done no read_group");
        assert.strictEqual(nbRPCs.searchRead, 0, "should have done no search_read");

        assert.containsOnce(list, 'tbody', "there should be 1 tbody");
        assert.containsN(list, '.o_group_header', 2,
            "should contain 2 groups at first level");
        assert.containsN(list, '.o_group_name .fa-caret-right', 2,
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

        assert.containsN(list, '.o_group_header', 2,
            "should contain 2 groups at first level");

        // open the first group
        testUtils.dom.click(list.$('.o_group_header:first'));

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
        testUtils.dom.click(list.$('.o_group_header'));
        assert.strictEqual(list.$('.o_group_header').css('height'), headerHeight,
            "height of group header shouldn't have changed");
        assert.hasClass(list.$('.o_group_header td:last'),'o_group_pager',
            "last cell of open group header should have classname 'o_group_header'");
        assert.strictEqual(list.$('.o_pager_value').text(), '1-3',
            "pager's value should be correct");
        assert.containsN(list, '.o_data_row', 3,
            "open group should display 3 records");

        // go to next page
        testUtils.dom.click(list.$('.o_pager_next'));
        assert.strictEqual(list.$('.o_pager_value').text(), '4-4',
            "pager's value should be correct");
        assert.containsOnce(list, '.o_data_row',
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

        assert.containsN(list, 'tr.o_data_row', 4,
            "should have 4 records");
        assert.strictEqual(list.$buttons.find('.o_list_button_add:visible').length, 1,
            "create button should be visible");
        assert.strictEqual(list.$buttons.find('.o_list_button_discard:visible').length, 0,
            "discard button should be hidden");
        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        assert.strictEqual(list.$buttons.find('.o_list_button_add:visible').length, 0,
            "create button should be hidden");
        assert.strictEqual(list.$buttons.find('.o_list_button_discard:visible').length, 1,
            "discard button should be visible");
        testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        assert.containsN(list, 'tr.o_data_row', 4,
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

        assert.containsN(list, 'tbody td.o_invisible_modifier', 3,
            "there should be 3 invisible foo cells in readonly mode");

        // Make first line editable
        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(1)'));

        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_invisible_modifier').length, 1,
            "the foo field widget should have been rendered as invisible");

        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]:not(.o_invisible_modifier)').length, 1,
            "the foo field widget should have been marked as non-invisible");
        assert.containsN(list, 'tbody td.o_invisible_modifier', 2,
            "the foo field widget parent cell should not be invisible anymore");

        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_invisible_modifier').length, 1,
            "the foo field widget should have been marked as invisible again");
        assert.containsN(list, 'tbody td.o_invisible_modifier', 3,
            "the foo field widget parent cell should now be invisible again");

        // Reswitch the cell to editable and save the row
        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        testUtils.dom.click(list.$('thead'));

        assert.containsN(list, 'tbody td.o_invisible_modifier', 2,
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

        assert.containsN(list, 'tbody td.o_readonly_modifier', 3,
            "there should be 3 readonly foo cells in readonly mode");

        // Make first line editable
        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(1)'));

        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > span[name="foo"]').length, 1,
            "the foo field widget should have been rendered as readonly");

        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]').length, 1,
            "the foo field widget should have been rerendered as editable");
        assert.containsN(list, 'tbody td.o_readonly_modifier', 2,
            "the foo field widget parent cell should not be readonly anymore");

        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > span[name="foo"]').length, 1,
            "the foo field widget should have been rerendered as readonly");
        assert.containsN(list, 'tbody td.o_readonly_modifier', 3,
            "the foo field widget parent cell should now be readonly again");

        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]').length, 1,
            "the foo field widget should have been rerendered as editable again");
        assert.containsN(list, 'tbody td.o_readonly_modifier', 2,
            "the foo field widget parent cell should not be readonly again");

        // Click outside to leave edition mode
        testUtils.dom.click(list.$el);

        assert.containsN(list, 'tbody td.o_readonly_modifier', 2,
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

        assert.containsN(list, 'tbody td.o_required_modifier', 3,
            "there should be 3 required foo cells in readonly mode");

        // Make first line editable
        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(1)'));

        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_required_modifier').length, 1,
            "the foo field widget should have been rendered as required");

        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"]:not(.o_required_modifier)').length, 1,
            "the foo field widget should have been marked as non-required");
        assert.containsN(list, 'tbody td.o_required_modifier', 2,
            "the foo field widget parent cell should not be required anymore");

        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        assert.strictEqual(list.$('tbody tr:nth(0) td:nth(1) > input[name="foo"].o_required_modifier').length, 1,
            "the foo field widget should have been marked as required again");
        assert.containsN(list, 'tbody td.o_required_modifier', 3,
            "the foo field widget parent cell should now be required again");

        // Reswitch the cell to editable and save the row
        testUtils.dom.click(list.$('tbody tr:nth(0) td:nth(2) input'));
        testUtils.dom.click(list.$('thead'));

        assert.containsN(list, 'tbody td.o_required_modifier', 2,
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
            services: {
                notification: NotificationService.extend({
                    notify: function (params) {
                        if (params.type === 'warning') {
                            warnings++;
                        }
                    }
                }),
            },
        });

        // Start first line edition
        var $firstFooTd = list.$('tbody tr:nth(0) td:nth(1)');
        testUtils.dom.click($firstFooTd);

        // Remove required foo field value
        testUtils.fields.editInput($firstFooTd.find('input'), "")

        // Try starting other line edition
        var $secondFooTd = list.$('tbody tr:nth(1) td:nth(1)');
        testUtils.dom.click($secondFooTd);

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

    QUnit.test('open a virtual id', function (assert) {
        assert.expect(1);

        var list = createView({
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

    QUnit.test('pressing enter on last line of editable list view', function (assert) {
        assert.expect(7);

        var list = createView({
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
        testUtils.dom.click(list.$('td:contains(gnap)'));
        assert.hasClass(list.$('tr.o_data_row:eq(2)'),'o_selected_row',
            "3rd row should be selected");

        // press enter in input
        list.$('tr.o_selected_row input').trigger({type: 'keydown', which: 13}); // enter
        assert.hasClass(list.$('tr.o_data_row:eq(3)'),'o_selected_row',
            "4rd row should be selected");
        assert.doesNotHaveClass(list.$('tr.o_data_row:eq(2)'), 'o_selected_row',
            "3rd row should no longer be selected");

        // press enter on last row
        list.$('tr.o_selected_row input').trigger({type: 'keydown', which: 13}); // enter
        assert.containsN(list, 'tr.o_data_row', 5, "should have created a 5th row");

        assert.verifySteps(['/web/dataset/search_read', '/web/dataset/call_kw/foo/default_get']);
        list.destroy();
    });

    QUnit.test('pressing tab on last cell of editable list view', function (assert) {
        assert.expect(9);

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

        testUtils.dom.click(list.$('td:contains(blip)').last());
        assert.strictEqual(document.activeElement.name, "foo",
            "focus should be on an input with name = foo");

        //it will not create a new line unless a modification is made
        document.activeElement.value = "blip-changed";
        $(document.activeElement).trigger({type: 'change'});

        list.$('tr.o_selected_row input[name="foo"]').trigger({type: 'keydown', which: 9}); // tab
        assert.strictEqual(document.activeElement.name, "int_field",
            "focus should be on an input with name = int_field");

        list.$('tr.o_selected_row input[name="int_field"]').trigger({type: 'keydown', which: 9}); // tab

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

        testUtils.dom.click(list.$('td:contains(-4)').last());

        testUtils.fields.editInput(list.$('tr.o_selected_row input[name="int_field"]'), '1234');
        list.$('tr.o_selected_row input[name="int_field"]').trigger({type: 'keydown', which: 9}); // tab

        defaultGetDef.resolve();
        assert.containsN(list, 'tbody tr.o_data_row', 4,
            "should have 4 data rows");
        readDef.resolve();
        assert.containsN(list, 'tbody tr.o_data_row', 5,
            "should have 5 data rows");
        assert.strictEqual(list.$('td:contains(1234)').length, 1,
            "should have a cell with new value");

        // we trigger a tab to move to the second cell in the current row. this
        // operation requires that this.currentRow is properly set in the
        // list editable renderer.
        list.$('tr.o_selected_row input[name="foo"]').trigger({type: 'keydown', which: 9}); // tab
        assert.hasClass(list.$('tr.o_data_row:eq(4)'),'o_selected_row',
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
                hasSidebar: true,
            },
        });

        var $dropdowns = $('.o_web_client .o_control_panel .btn-group .o_dropdown_toggler_btn');
        assert.strictEqual($dropdowns.length, 2,
            "there should be 2 dropdowns in the toolbar.");
        var $actions = $('.o_web_client .o_control_panel .btn-group .dropdown-menu')[1].children;
        assert.strictEqual($actions.length, 3,
            "there should be 3 actions");
        var $customAction = $('.o_web_client .o_control_panel .btn-group .dropdown-item:nth(2)');
        assert.strictEqual($customAction.text().trim(), 'Action event',
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

        testUtils.dom.click(list.$('.o_data_row:nth(2) > td:not(.o_list_record_selector)').first());
        assert.ok(list.$('.o_data_row:nth(2)').is('.o_selected_row'),
            "third row should be in edition");
        testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        assert.ok(list.$('.o_data_row:nth(0)').is('.o_selected_row'),
            "first row should be in edition (creation)");
        testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        assert.containsNone(list, '.o_selected_row',
            "no row should be selected");
        testUtils.dom.click(list.$('.o_data_row:nth(2) > td:not(.o_list_record_selector)').first());
        assert.ok(list.$('.o_data_row:nth(2)').is('.o_selected_row'),
            "third row should be in edition");
        assert.containsOnce(list, '.o_selected_row',
            "no other row should be selected");

        list.destroy();
    });

    QUnit.test('navigation with tab and readonly field (no modification)', function (assert) {
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
        testUtils.dom.click(list.$('td:contains(yop)').last());

        list.$('tr.o_selected_row input[name="foo"]').trigger({type: 'keydown', which: $.ui.keyCode.TAB});

        assert.hasClass(list.$('tr.o_data_row:eq(1)'),'o_selected_row',
            "2nd row should be selected");

        // we do it again. This was broken because the this.currentRow variable
        // was not properly set, and the second TAB could cause a crash.
        list.$('tr.o_selected_row input[name="foo"]').trigger({type: 'keydown', which: $.ui.keyCode.TAB});
        assert.hasClass(list.$('tr.o_data_row:eq(2)'),'o_selected_row',
            "3rd row should be selected");

        list.destroy();
    });


    QUnit.test('navigation with tab and readonly field (with modification)', function (assert) {
        // This test makes sure that if we have 2 cells in a row, the first in
        // edit mode, and the second one readonly, then if we press TAB when the
        // focus is on the first, then the focus skips the readonly cells and
        // directly goes to the next line instead.
        assert.expect(2);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="int_field" readonly="1"/></tree>',
        });

        // click on first td and press TAB
        testUtils.dom.click(list.$('td:contains(yop)').last());

        //modity the cell content
        document.activeElement.value = "blip-changed";
        $(document.activeElement).trigger({type: 'change'});

        list.$('tr.o_selected_row input[name="foo"]').trigger({type: 'keydown', which: $.ui.keyCode.TAB});

        assert.hasClass(list.$('tr.o_data_row:eq(1)'),'o_selected_row',
            "2nd row should be selected");

        // we do it again. This was broken because the this.currentRow variable
        // was not properly set, and the second TAB could cause a crash.
        list.$('tr.o_selected_row input[name="foo"]').trigger({type: 'keydown', which: $.ui.keyCode.TAB});
        assert.hasClass(list.$('tr.o_data_row:eq(2)'),'o_selected_row',
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

        assert.containsN(list, '.o_data_row', 4,
            "the list should contain 4 rows");

        testUtils.dom.click(list.$('.o_data_row:nth(2) .o_data_cell:first'));
        assert.hasClass(list.$('.o_data_row:nth(2)'),'o_selected_row',
            "third row should be in edition");

        // Press 'Tab' -> should go to next line
        // add a value in the cell because the Tab on an empty first cell would activate the next widget in the view
        testUtils.fields.editInput(list.$('.o_selected_row input').eq(1), 11);
        list.$('.o_selected_row input').trigger({type: 'keydown', which: 9});
        assert.hasClass(list.$('.o_data_row:nth(3)'),'o_selected_row',
            "fourth row should be in edition");

        // Press 'Tab' -> should go back to first line as the create action isn't available
        testUtils.fields.editInput(list.$('.o_selected_row input').eq(1), 11);
        list.$('.o_selected_row input').trigger({type: 'keydown', which: 9});
        assert.hasClass(list.$('.o_data_row:first'),'o_selected_row',
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
                    '<field name="foo"/>' +
                '</sheet></form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.containsN(form, '.o_field_widget[name=o2m] .o_data_row', 2,
            "there should be two records in the many2many");

        testUtils.dom.click(form.$('.o_field_widget[name=o2m] .o_data_cell:first'));
        assert.hasClass(form.$('.o_field_widget[name=o2m] .o_data_row:first'),'o_selected_row',
            "first row should be in edition");

        // Press 'Tab' -> should go to next line
        form.$('.o_field_widget[name=o2m] .o_selected_row input').trigger({type: 'keydown', which: 9});
        assert.hasClass(form.$('.o_field_widget[name=o2m] .o_data_row:nth(1)'),'o_selected_row',
            "second row should be in edition");

        // Press 'Tab' -> should get out of the one to many and go to the next field of the form
        form.$('.o_field_widget[name=o2m] .o_selected_row input').trigger({type: 'keydown', which: 9});
        assert.strictEqual(document.activeElement, form.$('input[name="foo"]')[0],
            "the next field should be selected");

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
        testUtils.dom.click(list.$('td:contains(yop)'));
        testUtils.fields.editSelect(list.$('tr.o_selected_row input[name="foo"]'), 'new value');
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

        testUtils.dom.click(list.$('td:contains(gnap)'));
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

        testUtils.dom.click(list.$('tbody tr:eq(2) td:eq(1)'));
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

        testUtils.dom.click(list.$('tbody tr:eq(2) td:eq(2)'));
        assert.strictEqual(list.$('tbody tr:eq(2) input[name="foo"]')[0], document.activeElement,
            "foo should be focused");
        list.$('tbody tr:eq(2) input[name="foo"]').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.strictEqual(list.$('tbody tr:eq(2) input[name="int_field"]')[0], document.activeElement,
            "int_field should be focused");

        list.destroy();
    });

    QUnit.test('navigation: not moving down with keydown', function (assert) {
        assert.expect(2);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/></tree>',
        });

        testUtils.dom.click(list.$('td:contains(yop)'));
        assert.hasClass(list.$('tr.o_data_row:eq(0)'),'o_selected_row',
            "1st row should be selected");
        list.$('tr.o_selected_row input[name="foo"]').trigger({type: 'keydown', which: $.ui.keyCode.DOWN});
        assert.hasClass(list.$('tr.o_data_row:eq(0)'),'o_selected_row',
            "1st row should still be selected");
        list.destroy();
    });

    QUnit.test('navigation: moving right with keydown from text field does not move the focus', function (assert) {
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

        testUtils.dom.click(list.$('td:contains(yop)'));
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
        assert.strictEqual(document.activeElement, list.$('textarea[name="foo"]')[0],
            "next field (checkbox) should now be focused");
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

        testUtils.dom.click(list.$('.o_data_cell:first'));
        testUtils.fields.editInput(list.$('input[name="foo"]'), "hello");
        testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));
        assert.strictEqual($('.modal:visible').length, 1,
            "a modal to ask for discard should be visible");

        testUtils.dom.click($('.modal:visible .btn-primary'));
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

        testUtils.dom.click(list.$('.o_data_cell:first'));

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

        testUtils.dom.click(list.$('.o_data_cell:first'));
        assert.verifySteps([], 'no switch view should have been requested');
        assert.containsOnce(list, '.o_selected_row',
            "a row should be in edition");
        testUtils.dom.click(list.$buttons.find('.o_list_button_discard'));

        // reload with groupBy
        list.reload({groupBy: ['bar']});

        // clicking on record should open the form view
        testUtils.dom.click(list.$('.o_group_header:first'));
        testUtils.dom.click(list.$('.o_data_cell:first'));

        // clicking on create button should open the form view
        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
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
        testUtils.dom.click(list.$('.o_group_header:first'));
        testUtils.dom.click(list.$('.o_data_cell:first'));

        // for the same reason, clicking on 'Create' should open the form view
        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        assert.verifySteps(['switch view form 1', 'switch view form false'],
            "two switch view to form should have been requested");

        // reload without groupBy
        list.reload({groupBy: []});

        // as the view is no longer grouped, it is editable, so clicking on a
        // row should switch it in edition
        testUtils.dom.click(list.$('.o_data_cell:first'));

        assert.verifySteps(['switch view form 1', 'switch view form false'],
            "no more switch view should have been requested");
        assert.containsOnce(list, '.o_selected_row',
            "a row should be in edition");

        // clicking on the body should leave the edition
        testUtils.dom.click($('body'));
        assert.containsNone(list, '.o_selected_row',
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

        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        list.$('input[name="foo"]').trigger({type: 'keydown', which: $.ui.keyCode.ESCAPE});
        assert.containsN(list, 'tr.o_data_row', 4,
            "should have 4 data row in list");
        assert.containsNone(list, 'tr.o_data_row.o_selected_row',
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

        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        list.$('input[name="foo"]').trigger({type: 'keydown', which: $.ui.keyCode.ESCAPE});
        assert.containsN(list, 'tr.o_data_row', 4,
            "should have 4 data row in list");
        assert.containsNone(list, 'tr.o_data_row.o_selected_row',
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
        testUtils.dom.dragAndDrop(
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
                    {id: 1, int_field: 11},
                    {id: 2, int_field: 12},
                    {id: 3, int_field: 13},
                    {id: 4, int_field: 14},
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
        testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').eq(2),
            {position: 'top'}
        );
        assert.strictEqual(list.$('tbody tr td.o_list_number').text(), '1243',
            "the int_field (sequence) should have been correctly updated");
        testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(2),
            list.$('tbody tr').eq(1),
            {position: 'top'}
        );
        assert.deepEqual(list.$('tbody tr td.o_list_number').text(), '1423',
            "the int_field (sequence) should have been correctly updated");
        testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(1),
            list.$('tbody tr').eq(3),
            {position: 'top'}
        );
        assert.deepEqual(list.$('tbody tr td.o_list_number').text(), '1243',
            "the int_field (sequence) should have been correctly updated");
        testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(2),
            list.$('tbody tr').eq(1),
            {position: 'top'}
        );
        assert.deepEqual(list.$('tbody tr td.o_list_number').text(), '1423',
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
        testUtils.dom.dragAndDrop(
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

        testUtils.dom.click(list.$('tbody tr:eq(1) td:last'));

        assert.strictEqual(list.$('tbody tr:eq(1) td:last input').val(), '0',
            "the edited record should be the good one");

        list.destroy();
    });

    QUnit.test('editable list, handle widget locks and unlocks on sort', function (assert) {
        assert.expect(6);

        // we need another sortable field to lock/unlock the handle
        this.data.foo.fields.amount.sortable = true;
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
                    '<field name="amount" widget="float"/>' +
                  '</tree>',
        });

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '1200.00500.00300.000.00',
            "default should be sorted by int_field");

        // Drag and drop the fourth line in second position
        testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        // Handle should be unlocked at this point
        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '1200.000.00500.00300.00',
            "drag and drop should have succeeded, as the handle is unlocked");

        // Sorting by a field different for int_field should lock the handle
        testUtils.dom.click(list.$('.o_column_sortable').eq(1));

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '0.00300.00500.001200.00',
            "should have been sorted by amount");

        // Drag and drop the fourth line in second position (not)
        testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '0.00300.00500.001200.00',
            "drag and drop should have failed as the handle is locked");

        // Sorting by int_field should unlock the handle
        testUtils.dom.click(list.$('.o_column_sortable').eq(0));

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '1200.000.00500.00300.00',
            "records should be ordered as per the previous resequence");

        // Drag and drop the fourth line in second position
        testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        assert.strictEqual(list.$('tbody span[name="amount"]').text(), '1200.00300.000.00500.00',
            "drag and drop should have worked as the handle is unlocked");

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
                    var _super = this._super.bind(this);
                    assert.strictEqual(args.offset, 1,
                        "should write the sequence starting from the lowest current one");
                    assert.strictEqual(args.field, 'int_field',
                        "should write the right field as sequence");
                    assert.deepEqual(args.ids, [4, 2, 3],
                        "should write the sequence in correct order");
                    return $.when(def).then(function () {
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
        testUtils.dom.dragAndDrop(
            list.$('.ui-sortable-handle').eq(3),
            list.$('tbody tr').first(),
            {position: 'bottom'}
        );

        // edit moved row before the end of resequence
        testUtils.dom.click(list.$('tbody tr:eq(3) td:last'));

        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').length, 0,
            "shouldn't edit the line before resequence");

        def.resolve();

        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').length, 1,
            "should edit the line after resequence");

        assert.strictEqual(list.$('tbody tr:eq(3) td:last input').val(), '300',
            "fourth record should have amount 300");

        testUtils.fields.editInput(list.$('tbody tr:eq(3) td:last input'), 301);
        testUtils.dom.click(list.$('tbody tr:eq(0) td:last'));

        testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        assert.strictEqual(list.$('tbody tr:eq(0) td:last').text(), '1200',
            "first record should have amount 1200");
        assert.strictEqual(list.$('tbody tr:eq(1) td:last').text(), '0',
            "second record should have amount 1");
        assert.strictEqual(list.$('tbody tr:eq(2) td:last').text(), '500',
            "third record should have amount 500");
        assert.strictEqual(list.$('tbody tr:eq(3) td:last').text(), '301',
            "fourth record should have amount 301");

        testUtils.dom.click(list.$('tbody tr:eq(3) td:last'));
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

        assert.containsN(list, '.o_data_row', 4,
            "should contain 4 records");

        // click on Add twice, and delay the onchange
        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

        def.resolve();

        assert.containsN(list, '.o_data_row', 5,
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
        assert.strictEqual(list.$('tbody td:not(.o_list_record_selector)').text(), "Value 1USDEUREUR",
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

        testUtils.dom.click(list.$('.o_data_cell:first'));
        testUtils.fields.editInput(list.$('.o_field_widget[name=foo]'), 'abc');
        testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

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

        testUtils.dom.click(list.$('.o_group_header:first'));
        assert.containsOnce(list, '.o_data_row:first .o_toggle_button_success',
            "boolean value of the first record should be true");
        testUtils.dom.click(list.$('.o_data_row:first .o_icon_button'));
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
        testUtils.dom.click(list.$('.o_group_header:first'));
        assert.strictEqual(list.$('th.o_group_name').eq(1).children().length, 1,
            "There should be an empty element creating the indentation for the subgroup.");
        assert.hasClass(list.$('th.o_group_name').eq(1).children().eq(0), 'fa',
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

        assert.containsN(list, '.o_data_row', 2,
            'should display 2 data rows');
        list.destroy();
    });

    QUnit.test('check if the view destroys all widgets and instances', function (assert) {
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

        var list = createView(params);
        list.destroy();

        var initialInstanceNumber = instanceNumber;
        instanceNumber = 0;

        list = createView(params);

        // call destroy function of controller to ensure that it correctly destroys everything
        list.__destroy();

        assert.strictEqual(instanceNumber, initialInstanceNumber + 3, "every widget must be destroyed exept the parent");

        list.destroy();

        testUtils.mock.unpatch(mixins.ParentedMixin);
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

        assert.containsN(list, '.o_list_view .o_data_row', 4,
            "list view should contain 4 records");

        // reload with a domain (this request is blocked)
        blockSearchRead = true;
        list.reload({domain: [['foo', '=', 'yop']]});

        assert.containsN(list, '.o_list_view .o_data_row', 4,
            "list view should still contain 4 records (search_read being blocked)");

        // reload without the domain
        blockSearchRead = false;
        list.reload({domain: []});

        // unblock the RPC
        def.resolve();
        assert.containsN(list, '.o_list_view .o_data_row', 4,
            "list view should still contain 4 records");

        list.destroy();
    });

    QUnit.test('list view on a "noCache" model', function (assert) {
        assert.expect(8);

        testUtils.mock.patch(BasicModel, {
            noCacheModels: BasicModel.prototype.noCacheModels.concat(['foo']),
        });

        var list = createView({
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
        testUtils.dom.click(list.$buttons.find('.o_list_button_add'));
        testUtils.fields.editInput(list.$('.o_selected_row .o_field_widget'), 'some value');
        testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        // edit an existing record
        testUtils.dom.click(list.$('.o_data_cell:first'));
        testUtils.fields.editInput(list.$('.o_selected_row .o_field_widget'), 'new value');
        testUtils.dom.click(list.$buttons.find('.o_list_button_save'));

        // delete a record
        testUtils.dom.click(list.$('.o_data_row:first .o_list_record_selector input'));
        testUtils.dom.click(list.sidebar.$('.o_dropdown_toggler_btn:contains(Action)'));
        testUtils.dom.click(list.sidebar.$('a:contains(Delete)'));
        testUtils.dom.click($('.modal-footer .btn-primary'));

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
    });

    QUnit.test('list should ask to scroll to top on page changes', function (assert) {
        assert.expect(10);

        var list = createView({
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
        testUtils.dom.click(list.pager.$('.o_pager_next'));
        testUtils.dom.click(list.pager.$('.o_pager_previous'));

        assert.verifySteps(['scroll', 'scroll'],
            "should ask to scroll when switching pages");

        // change the limit (should not ask to scroll)
        testUtils.dom.click(list.pager.$('.o_pager_value'));
        list.pager.$('.o_pager_value input').val('1-2').blur();
        assert.strictEqual(list.pager.$('.o_pager_value').text(), '1-2',
            "should have changed the limit");

        assert.verifySteps(['scroll', 'scroll'],
            "should not ask to scroll when changing the limit");

        // switch pages again (should still ask to scroll)
        testUtils.dom.click(list.pager.$('.o_pager_next'));

        assert.verifySteps(['scroll', 'scroll', 'scroll'],
            "this is still working after a limit change");

        list.destroy();
    });

    QUnit.test('list with handle field, override default_get, bottom when inline', function (assert) {
        assert.expect(2);

        this.data.foo.fields.int_field.default = 10;

        var list = createView({
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
        testUtils.dom.click($('.o_list_button_add'));
        testUtils.fields.editInput(list.$('.o_input[name="foo"]'), inputText);
        testUtils.dom.click($('.o_list_button_save'));
        testUtils.dom.click($('.o_list_button_add'));

        assert.strictEqual($('.o_data_cell').text(), "blipblipyopgnap" + inputText);

        list.destroy();
    });
});

});
