odoo.define('sale.dashboard_tests', function (require) {
"use strict";

var KanbanView = require('web.KanbanView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Sales Team Dashboard', {
    beforeEach: function () {
        this.data = {
            'crm.team': {
                fields: {
                    foo: {string: "Foo", type: 'char'},
                    invoiced_target: {string: "Invoiced_target", type: 'integer'},
                },
                records: [
                    {id: 1, foo: "yop"},
                ],
            },
        };
    }
});

QUnit.test('edit target with several o_kanban_primary_bottom divs [REQUIRE FOCUS]', async function (assert) {
    assert.expect(6);

    var kanban = await createView({
        View: KanbanView,
        model: 'crm.team',
        data: this.data,
        arch: '<kanban>' +
                '<templates>' +
                    '<t t-name="kanban-box">' +
                        '<div class="container o_kanban_card_content">' +
                            '<field name="invoiced_target" />' +
                            '<a href="#" class="sales_team_target_definition o_inline_link">' +
                                'Click to define a target</a>' +
                            '<div class="col-12 o_kanban_primary_bottom"/>' +
                            '<div class="col-12 o_kanban_primary_bottom bottom_block"/>' +
                        '</div>' +
                    '</t>' +
                '</templates>' +
              '</kanban>',
        mockRPC: function (route, args) {
            if (args.method === 'write') {
                assert.strictEqual(args.args[1].invoiced_target, 123,
                    "new value is correctly saved");
            }
            if (args.method === 'read') { // Read happens after the write
                assert.deepEqual(args.args[1], ['invoiced_target', 'display_name'],
                    'the read (after write) should ask for invoiced_target');
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.containsOnce(kanban, '.o_kanban_view .sales_team_target_definition',
        "should have classname 'sales_team_target_definition'");
    assert.containsN(kanban, '.o_kanban_primary_bottom', 2,
        "should have two divs with classname 'o_kanban_primary_bottom'");

    await testUtils.dom.click(kanban.$('a.sales_team_target_definition'));
    assert.containsOnce(kanban, '.o_kanban_primary_bottom:last input',
        "should have rendered an input in the last o_kanban_primary_bottom div");

    kanban.$('.o_kanban_primary_bottom:last input').focus();
    kanban.$('.o_kanban_primary_bottom:last input').val('123');
    kanban.$('.o_kanban_primary_bottom:last input').trigger('blur');
    await testUtils.nextTick();
    assert.strictEqual(kanban.$('.o_kanban_record').text(), "123Click to define a target",
        'The kanban record should display the updated target value');

    kanban.destroy();
});

QUnit.test('edit target supports push Enter', async function (assert) {
    assert.expect(3);

    var kanban = await createView({
        View: KanbanView,
        model: 'crm.team',
        data: this.data,
        arch: '<kanban>' +
                '<templates>' +
                    '<t t-name="kanban-box">' +
                        '<div class="container o_kanban_card_content">' +
                            '<field name="invoiced_target" />' +
                            '<a href="#" class="sales_team_target_definition o_inline_link">' +
                                'Click to define a target</a>' +
                            '<div class="col-12 o_kanban_primary_bottom"/>' +
                            '<div class="col-12 o_kanban_primary_bottom bottom_block"/>' +
                        '</div>' +
                    '</t>' +
                '</templates>' +
              '</kanban>',
        mockRPC: function (route, args) {
            if (args.method === 'write') {
                assert.strictEqual(args.args[1].invoiced_target, 123,
                    "new value is correctly saved");
            }
            if (args.method === 'read') { // Read happens after the write
                assert.deepEqual(args.args[1], ['invoiced_target', 'display_name'],
                    'the read (after write) should ask for invoiced_target');
            }
            return this._super.apply(this, arguments);
        },
    });

    await testUtils.dom.click(kanban.$('a.sales_team_target_definition'));

    kanban.$('.o_kanban_primary_bottom:last input').focus();
    kanban.$('.o_kanban_primary_bottom:last input').val('123');
    kanban.$('.o_kanban_primary_bottom:last input').trigger($.Event('keydown', {which: $.ui.keyCode.ENTER, keyCode: $.ui.keyCode.ENTER}));
    await testUtils.nextTick();
    assert.strictEqual(kanban.$('.o_kanban_record').text(), "123Click to define a target",
        'The kanban record should display the updated target value');

    kanban.destroy();
});

});
