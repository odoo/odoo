odoo.define('web.base_import_tests', function (require) {
"use strict";

const KanbanView = require('web.KanbanView');
const ListView = require('web.ListView');
const PivotView = require('web.PivotView');
const testUtils = require('web.test_utils');

const createView = testUtils.createView;

QUnit.module('Base Import Tests', {
    beforeEach: function () {
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

QUnit.test('import in favorite dropdown in list', async function (assert) {
    assert.expect(2);

    const list = await createView({
        View: ListView,
        model: 'foo',
        data: this.data,
        arch: '<tree><field name="foo"/></tree>',
    });

    testUtils.mock.intercept(list, 'do_action', function () {
        assert.ok(true, "should have triggered a do_action");
    });

    await testUtils.dom.click(list.$('.o_favorite_menu button'));
    assert.containsOnce(list, '.o_import_menu');

    await testUtils.dom.click(list.$('.o_import_menu button'));

    list.destroy();
});

QUnit.test('import favorite dropdown item should not in list with create="0"', async function (assert) {
    assert.expect(1);

    const list = await createView({
        View: ListView,
        model: 'foo',
        data: this.data,
        arch: '<tree create="0"><field name="foo"/></tree>',
    });

    await testUtils.dom.click(list.$('.o_favorite_menu button'));
    assert.containsNone(list, '.o_import_menu');

    list.destroy();
});

QUnit.test('import favorite dropdown item should not in list with import="0"', async function (assert) {
    assert.expect(1);

    const list = await createView({
        View: ListView,
        model: 'foo',
        data: this.data,
        arch: '<tree import="0"><field name="foo"/></tree>',
    });

    await testUtils.dom.click(list.$('.o_favorite_menu button'));
    assert.containsNone(list, '.o_import_menu');

    list.destroy();
});

QUnit.test('import in favorite dropdown in kanban', async function (assert) {
    assert.expect(2);

    const kanban = await createView({
        View: KanbanView,
        model: 'foo',
        data: this.data,
        arch: `<kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t>
                </templates>
            </kanban>`,
    });

    testUtils.mock.intercept(kanban, 'do_action', function () {
        assert.ok(true, "should have triggered a do_action");
    });

    await testUtils.dom.click(kanban.$('.o_favorite_menu button'));
    assert.containsOnce(kanban, '.o_import_menu');

    await testUtils.dom.click(kanban.$('.o_import_menu button'));

    kanban.destroy();
});

QUnit.test('import favorite dropdown item should not in list with create="0"', async function (assert) {
    assert.expect(1);

    const kanban = await createView({
        View: KanbanView,
        model: 'foo',
        data: this.data,
        arch: `<kanban create="0">
                <templates>
                    <t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t>
                </templates>
            </kanban>`,
    });

    await testUtils.dom.click(kanban.$('.o_favorite_menu button'));
    assert.containsNone(kanban, '.o_import_menu');

    kanban.destroy();
});

QUnit.test('import dropdown favorite should not in kanban with import="0"', async function (assert) {
    assert.expect(1);

    const kanban = await createView({
        View: KanbanView,
        model: 'foo',
        data: this.data,
        arch: `<kanban import="0">
                <templates>
                    <t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t>
                </templates>
            </kanban>`,
    });

    await testUtils.dom.click(kanban.$('.o_favorite_menu button'));
    assert.containsNone(kanban, '.o_import_menu');

    kanban.destroy();
});

QUnit.test('import should not available in favorite dropdown in pivot (other than kanban or list)', async function (assert) {
    assert.expect(1);

    this.data.foo.fields.foobar = { string: "Fubar", type: "integer", group_operator: 'sum' };

    const pivot = await createView({
        View: PivotView,
        model: 'foo',
        data: this.data,
        arch: '<pivot><field name="foobar" type="measure"/></pivot>',
    });

    await testUtils.dom.click(pivot.$('.o_favorite_menu button'));
    assert.containsNone(pivot, '.o_import_menu');

    pivot.destroy();
});

});
