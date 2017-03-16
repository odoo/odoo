odoo.define('web.list_tests', function (require) {
"use strict";

var config = require('web.config');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

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
                    m2m: {string: "M2M field", type: "many2many", relation: "bar"},
                    amount: {string: "Monetary field", type: "monetary"},
                    currency_id: {string: "Currency", type: "many2one",
                                  relation: "res_currency", default: 1},
                    datetime: {string: "Datetime Field", type: 'datetime'},
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
                    },
                    {id: 2, bar: true, foo: "blip", int_field: 9, qux: 13,
                     m2o: 2, m2m: [1, 2, 3], amount: 500},
                    {id: 3, bar: true, foo: "gnap", int_field: 17, qux: -3,
                     m2o: 1, m2m: [], amount: 300},
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
            }
        };
    }
}, function () {

    QUnit.module('ListView');

    QUnit.test('simple readonly list', function (assert) {
        assert.expect(7);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="int_field"/></tree>',
        });

        // 3 th (1 for checkbox, 2 for columns)
        assert.strictEqual(list.$('th').length, 3, "should have 3 columns");

        assert.strictEqual(list.$('td:contains(gnap)').length, 1, "should contain gnap");
        assert.strictEqual(list.$('tbody tr').length, 4, "should have 4 rows");
        assert.strictEqual(list.$('th.o_column_sortable').length, 1, "should have 1 sortable column");

        assert.ok(list.$buttons.find('.o_list_button_add').is(':visible'),
            "should have a visible Create button");
        assert.ok(!list.$buttons.find('.o_list_button_save').is(':visible'),
            "should not have a visible save button");
        assert.ok(!list.$buttons.find('.o_list_button_discard').is(':visible'),
            "should not have a visible save button");
        list.destroy();
    });


    QUnit.test('simple editable rendering', function (assert) {
        assert.expect(9);

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
        assert.expect(3);

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
        assert.ok(!$td.hasClass('o_edit_mode'), "foo cells should not be editable");
        assert.ok($second_td.hasClass('o_edit_mode'), "bar cells should be editable");
        assert.ok(!$third_td.hasClass('o_edit_mode'), "int_field cells should not be editable");
        list.destroy();
    });

    QUnit.test('basic operations for editable list renderer', function (assert) {
        assert.expect(4);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom"><field name="foo"/><field name="bar"/></tree>',
        });

        var $td = list.$('td:not(.o_list_record_selector)').first();
        assert.strictEqual($td.hasClass('o_edit_mode'), false, "td should not be in edit mode");
        $td.click();
        assert.strictEqual($td.hasClass('o_edit_mode'), true, "td should be in edit mode");
        assert.strictEqual($td.hasClass('o_field_dirty'), false, "td should not be dirty");
        $td.find('input').val('abc').trigger('input');
        assert.strictEqual($td.hasClass('o_field_dirty'), true, "td should be dirty");
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
            n = 1;
        });
        $td.click();
        $td.find('input').val('abc').trigger('input');
        assert.strictEqual(n, 1, "field_changed should not have been triggered");
        list.$('td:not(.o_list_record_selector)').eq(2).click();
        assert.strictEqual(n, 1, "field_changed should have been triggered");
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

    QUnit.test('aggregates are computed correctly', function (assert) {
        assert.expect(3);

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

        var $group_1_header = list.$('.o_group_header').filter(function (index, el) {
            return $(el).data('group').res_id === 1;
        });
        var $group_2_header = list.$('.o_group_header').filter(function (index, el) {
            return $(el).data('group').res_id === 2;
        });
        assert.strictEqual($group_1_header.find('td:nth(1)').text(), "23", "first group total should be 23");
        assert.strictEqual($group_2_header.find('td:nth(1)').text(), "9", "second group total should be 9");
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "32", "total should be 32");

        $group_1_header.click();
        list.$('tbody .o_list_record_selector input').first().click();
        assert.strictEqual(list.$('tfoot td:nth(2)').text(), "10",
                        "total should be 10 as first record of first group is selected");
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

    QUnit.test('can display button in edit mode', function (assert) {
        assert.expect(1);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<button name="notafield" type="object" icon="fa-asterisk"/>' +
                '</tree>',
        });
        assert.ok(list.$('tbody button').length, "should have a button");
        list.destroy();
    });

    QUnit.test('can display a list with a many2many field', function (assert) {
        assert.expect(2);

        var rpcCount = 0;

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="m2m"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                rpcCount++;
                return this._super(route, args);
            }
        });
        assert.strictEqual(rpcCount, 2, "should have done 2 rpcs: 1 searchread and 1 read for m2m");
        assert.ok(list.$('td:contains(Value 1, Value 2, Value 3)').length,
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
        assert.expect(9);

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


        assert.ok(list.$('tbody tr:eq(0) td:eq(1)').hasClass('o_edit_mode'),
            "the date field td should be in edit mode");
        assert.strictEqual(list.$('tbody tr:eq(0) td:eq(1)').text().trim(), "",
            "the date field td should not have any content");

        list.$buttons.find('.o_list_button_save').click();
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
        assert.expect(6);

        var list = createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree>' +
                    '<field name="foo"/>' +
                    '<button string="a button" name="button_action" icon="fa-car" type="object"/>' +
                '</tree>',
            intercepts: {
                execute_action: function (event) {
                    assert.strictEqual(event.data.record_id, 1,
                        'should call with correct id');
                    assert.strictEqual(event.data.model, 'foo',
                        'should call with correct model');
                    assert.strictEqual(event.data.action_data.name, 'button_action',
                        "should call correct method");
                    assert.strictEqual(event.data.action_data.type, 'object',
                        'should have correct type');
                },
            },
        });

        assert.strictEqual(list.$('.o_list_button').length, 4,
            "there should be one button per row");
        assert.strictEqual(list.$('.o_list_button:first .o_icon_button .fa.fa-car').length, 1,
            'buttons should have correct icon');

        list.$('.o_list_button:first > button').click(); // click on the button
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
        assert.equal(list.$('tbody tr:nth(0) td:nth(4)').html(), "",
            "td that contains an invisible field should be empty");
        assert.equal(list.$('tbody tr:nth(0) td:nth(1)').html(), "",
            "td that contains an invisible button should be empty");
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
        });

        // FIXME: this test is locale dependant. we need to do it right.
        assert.strictEqual(list.$('td:contains(01/25/2017)').length, 1,
            "should have formatted the date");
        assert.strictEqual(list.$('td:contains(12/12/2016 10:55:05)').length, 1,
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

        assert.ok(list.$('.o_data_row:first td:nth(1)').hasClass('o_readonly'),
            "foo field cells should have class 'o_readonly'");

        // edit the first row
        list.$('.o_data_row:first td:nth(1)').click();
        assert.ok(list.$('.o_data_row:first').hasClass('o_selected_row'),
            "first row should be selected");
        assert.ok(list.$('.o_data_row:first td:nth(1)').hasClass('o_readonly'),
            "foo field cells should have class 'o_readonly'");
        assert.strictEqual(list.$('.o_data_row:first td:nth(1)').text(), 'yop',
            "no widget should be rendered for readonly fields");
        assert.ok(list.$('.o_data_row:first td:nth(2)').hasClass('o_edit_mode'),
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
});

});
