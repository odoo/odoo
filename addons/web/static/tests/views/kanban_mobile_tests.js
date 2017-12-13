odoo.define('web.kanban_mobile_tests', function (require) {
"use strict";

var KanbanView = require('web.KanbanView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "boolean"},
                    int_field: {string: "int_field", type: "integer", sortable: true},
                    qux: {string: "my float", type: "float"},
                    product_id: {string: "something_id", type: "many2one", relation: "product"},
                    category_ids: { string: "categories", type: "many2many", relation: 'category'},
                    state: { string: "State", type: "selection", selection: [["abc", "ABC"], ["def", "DEF"], ["ghi", "GHI"]]},
                    date: {string: "Date Field", type: 'date'},
                    datetime: {string: "Datetime Field", type: 'datetime'},
                },
                records: [
                    {id: 1, bar: true, foo: "yop", int_field: 10, qux: 0.4, product_id: 3, state: "abc", category_ids: []},
                    {id: 2, bar: true, foo: "blip", int_field: 9, qux: 13, product_id: 5, state: "def", category_ids: [6]},
                    {id: 3, bar: true, foo: "gnap", int_field: 17, qux: -3, product_id: 3, state: "ghi", category_ids: [7]},
                    {id: 4, bar: false, foo: "blip", int_field: -4, qux: 9, product_id: 5, state: "ghi", category_ids: []},
                    {id: 5, bar: false, foo: "Hello \"World\"! #peace_n'_love", int_field: -9, qux: 10, state: "jkl", category_ids: []},
                ]
            },
            product: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    name: {string: "Display Name", type: "char"},
                },
                records: [
                    {id: 3, name: "hello"},
                    {id: 5, name: "xmo"},
                ]
            },
            category: {
                fields: {
                    name: {string: "Category Name", type: "char"},
                    color: {string: "Color index", type: "integer"},
                },
                records: [
                    {id: 6, name: "gold", color: 2},
                    {id: 7, name: "silver", color: 5},
                ]
            },
        };
    },
}, function () {

    QUnit.module('KanbanView Mobile');

    QUnit.test('mobile grouped rendering', function (assert) {
        assert.expect(9);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test o_kanban_small_column" on_create="quick_create">' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates>' +
                '</kanban>',
            domain: [['product_id', '!=', false]],
            groupBy: ['product_id'],
        });

        // basic rendering tests
        assert.strictEqual(kanban.$('.o_kanban_group').length, 2, "should have 2 columns" );
        assert.ok(kanban.$('.o_kanban_mobile_tab:first').hasClass('o_current'),
            "first tab is the active tab with class 'o_current'");
        assert.strictEqual(kanban.$('.o_kanban_group:first > div.o_kanban_record').length, 2,
            "there are 2 records in active tab");
        assert.strictEqual(kanban.$('.o_kanban_group:nth(1) > div.o_kanban_record').length, 0,
            "there is no records in next tab. Records will be loaded when it will be opened");

        // quick create in first column
        kanban.$buttons.find('.o-kanban-button-new').click();
        assert.ok(kanban.$('.o_kanban_group:nth(0) > div:nth(1)').hasClass('o_kanban_quick_create'),
            "clicking on create should open the quick_create in the first column");

        // move to second column
        kanban.$('.o_kanban_mobile_tab:nth(1)').trigger('click');
        assert.ok(kanban.$('.o_kanban_mobile_tab:nth(1)').hasClass('o_current'),
            "second tab is now active with class 'o_current'");
        assert.strictEqual(kanban.$('.o_kanban_group:nth(1) > div.o_kanban_record').length, 2,
            "the 2 records of the second group have now been loaded");

        // quick create in second column
        kanban.$buttons.find('.o-kanban-button-new').click();
        assert.ok(kanban.$('.o_kanban_group:nth(1) >  div:nth(1)').hasClass('o_kanban_quick_create'),
            "clicking on create should open the quick_create in the second column");

        // kanban column should match kanban mobile tabs
        var column_ids = kanban.$('.o_kanban_group').map(function(){ return $(this).data('id') }).get();
        var tab_ids = kanban.$('.o_kanban_mobile_tab').map(function(){ return $(this).data('id') }).get();
        assert.deepEqual(column_ids, tab_ids, "all columns data-id should match mobile tabs data-id");

        kanban.destroy();
    });
    QUnit.test('mobile grouped with undefined column', function (assert) {
        assert.expect(3);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test o_kanban_small_column">' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates>' +
                '</kanban>',
            groupBy: ['product_id'],
        });

        // first column should be undefined with framework unique identifier
        assert.strictEqual(kanban.$('.o_kanban_group').length, 3, "should have 3 columns" );
        assert.strictEqual(kanban.$('.o_kanban_group:first-child[data-id^="partner_"]').length, 1,
            "Undefined column should be first and have unique framework identifier as data-id")

        // kanban column should match kanban mobile tabs
        var column_ids = kanban.$('.o_kanban_group').map(function(){ return $(this).data('id') }).get();
        var tab_ids = kanban.$('.o_kanban_mobile_tab').map(function(){ return $(this).data('id') }).get();
        assert.deepEqual(column_ids, tab_ids, "all columns data-id should match mobile tabs data-id");

        kanban.destroy();
    });
    QUnit.test('mobile grouped on many2one rendering', function (assert) {
        assert.expect(3);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test o_kanban_small_column">' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates>' +
                '</kanban>',
            groupBy: ['foo'],
        });

        // basic rendering tests
        assert.strictEqual(kanban.$('.o_kanban_group').length, 4, "should have 4 columns" );
        assert.strictEqual(kanban.$('.o_kanban_group[data-id^="partner_"]').length, 4,
            "all column should have framework unique identifiers");

        // kanban column should match kanban mobile tabs
        var column_ids = kanban.$('.o_kanban_group').map(function(){ return $(this).data('id') }).get();
        var tab_ids = kanban.$('.o_kanban_mobile_tab').map(function(){ return $(this).data('id') }).get();
        assert.deepEqual(column_ids, tab_ids, "all columns data-id should match mobile tabs data-id");

        kanban.destroy();
    });
});
});
