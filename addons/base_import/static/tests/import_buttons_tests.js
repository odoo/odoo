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

QUnit.test('add import button in list', async function(assert) {
    assert.expect(2);

    var list = await createView({
        View: ListView,
        model: 'foo',
        data: this.data,
        arch: '<tree><field name="foo"/></tree>',
    });

    assert.isVisible(list.$buttons.find('.o_button_import:contains(Import)'),
        "should have a visible Import button");

    testUtils.mock.intercept(list, 'do_action', function() {
        assert.ok(true, "should have triggered a do_action");
    });

    await testUtils.dom.click(list.$buttons.find('.o_button_import:contains(Import)'));
    list.destroy();
});

QUnit.test('list without import button', async function(assert) {
    assert.expect(1);

    var list = await createView({
        View: ListView,
        model: 'foo',
        data: this.data,
        arch: '<tree><field name="foo"/></tree>',
        viewOptions: {
            import_enabled: false,
        }
    });

    assert.containsNone(list.$buttons, '.o_button_import', 'should not have an Import button');
    list.destroy();
});

QUnit.test('add import button in kanban', async function(assert) {
    assert.expect(2);

    var kanban = await createView({
        View: KanbanView,
        model: 'foo',
        data: this.data,
        arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                    '<field name="foo"/>' +
                    '</div>' +
                '</t></templates></kanban>',
    });

    assert.isVisible(kanban.$buttons.find('.o_button_import:contains(Import)'),
        "should have a visible Import button");

    testUtils.mock.intercept(kanban, 'do_action', function() {
        assert.ok(true, "should have triggered a do_action");
    });

    await testUtils.dom.click(kanban.$buttons.find('.o_button_import:contains(Import)'));
    kanban.destroy();
});

QUnit.test('kanban without import button', async function(assert) {
    assert.expect(1);

    var kanban = await createView({
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

    assert.containsNone(kanban.$buttons, '.o_button_import', "should not have an Import button");
    kanban.destroy();
});

QUnit.test('import attrs in list views', async function (assert) {
    assert.expect(1);

    var list = await createView({
        View: ListView,
        model: 'foo',
        data: this.data,
        arch: '<tree import="0"><field name="foo"/></tree>',
    });

    assert.containsNone(list.$buttons, '.o_button_import');
    list.destroy();
});

QUnit.test('import attrs in kanban views', async function (assert) {
    assert.expect(1);

    var kanban = await createView({
        View: KanbanView,
        model: 'foo',
        data: this.data,
        arch: '<kanban import="0">' +
                '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                '</t></templates>' +
            '</kanban>',
    });

    assert.containsNone(kanban.$buttons, '.o_button_import');
    kanban.destroy();
});
});
