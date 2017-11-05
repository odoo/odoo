odoo.define('web.base_import_tests', function (require) {
"use strict";

var KanbanView = require('web.KanbanView');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Base Import Tests', {
    beforeEach: function() {
        this.data = {
            foo: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                },
                records: [
                    {id: 1, foo: "yop"},
                ]
            },
        };
    }
});

QUnit.test('add import button in list', function(assert) {
    assert.expect(2);

    var list = createView({
        View: ListView,
        model: 'foo',
        data: this.data,
        arch: '<tree><field name="foo"/></tree>',
    });

    assert.ok(list.$buttons.find('.o_button_import:contains(Import)').is(':visible'),
        "should have a visible Import button");

    testUtils.intercept(list, 'do_action', function() {
        assert.ok(true, "should have triggered a do_action");
    });

    list.$buttons.find('.o_button_import:contains(Import)').click();
    list.destroy();
});

QUnit.test('list without import button', function(assert) {
    assert.expect(1);

    var list = createView({
        View: ListView,
        model: 'foo',
        data: this.data,
        arch: '<tree><field name="foo"/></tree>',
        viewOptions: {
            import_enabled: false,
        }
    });

    assert.ok(!list.$buttons.find('.o_button_import').length, "should not have an Import button");
    list.destroy();
});

QUnit.test('add import button in kanban', function(assert) {
    assert.expect(2);

    var kanban = createView({
        View: KanbanView,
        model: 'foo',
        data: this.data,
        arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                    '<field name="foo"/>' +
                    '</div>' +
                '</t></templates></kanban>',
    });

    assert.ok(kanban.$buttons.find('.o_button_import:contains(Import)').is(':visible'),
        "should have a visible Import button");

    testUtils.intercept(kanban, 'do_action', function() {
        assert.ok(true, "should have triggered a do_action");
    });

    kanban.$buttons.find('.o_button_import:contains(Import)').click();
    kanban.destroy();
});

QUnit.test('kanban without import button', function(assert) {
    assert.expect(1);

    var kanban = createView({
        View: KanbanView,
        model: 'foo',
        data: this.data,
        arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                    '<field name="foo"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        viewOptions: {
            import_enabled: false,
        }
    });

    assert.ok(!kanban.$buttons.find('.o_button_import').length, "should not have an Import button");
    kanban.destroy();
});

});