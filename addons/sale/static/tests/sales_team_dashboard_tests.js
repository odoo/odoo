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
                    invoiced: {string: "Invoiced", type: 'integer'},
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
    assert.expect(7);

    var kanban = await createView({
        View: KanbanView,
        model: 'crm.team',
        data: this.data,
        arch: '<kanban>' +
                '<field name="invoiced_target"/>' +
                '<templates>' +
                    '<t t-name="kanban-box">' +
                        '<div class="container o_kanban_card_content">' +
                            `<field name="invoiced" widget="sales_team_progressbar" options="{'current_value': 'invoiced', 'max_value': 'invoiced_target', 'editable': true, 'edit_max_value': true}"/> ` +
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
                assert.deepEqual(args.args[1], ['invoiced_target', 'invoiced', 'display_name'],
                    'the read (after write) should ask for invoiced_target');
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.containsOnce(kanban, '.o_legacy_kanban_view .o_progressbar:contains(Click to define an invoicing target)')
    assert.containsN(kanban, '.o_kanban_primary_bottom', 2,
        "should have two divs with classname 'o_kanban_primary_bottom'");

    assert.containsNone(kanban, '.o_progressbar input')
    await testUtils.dom.click(kanban.$('.o_progressbar a'));
    assert.containsOnce(kanban, '.o_progressbar input')

    kanban.$('.o_progressbar input').focus();
    kanban.$('.o_progressbar input').val('123');
    kanban.$('.o_progressbar input').trigger('blur');
    await testUtils.nextTick();
    assert.strictEqual(kanban.$('.o_kanban_record').text().trim(), "0 / 123");

    kanban.destroy();
});

QUnit.test('edit target supports push Enter', async function (assert) {
    assert.expect(3);

    var kanban = await createView({
        View: KanbanView,
        model: 'crm.team',
        data: this.data,
        arch: '<kanban>' +
                '<field name="invoiced_target"/>' +
                '<templates>' +
                    '<t t-name="kanban-box">' +
                        '<div class="container o_kanban_card_content">' +
                            `<field name="invoiced" widget="sales_team_progressbar" options="{'current_value': 'invoiced', 'max_value': 'invoiced_target', 'editable': true, 'edit_max_value': true}"/> ` +
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
                assert.deepEqual(args.args[1], ['invoiced_target', 'invoiced', 'display_name'],
                    'the read (after write) should ask for invoiced_target');
            }
            return this._super.apply(this, arguments);
        },
    });

    await testUtils.dom.click(kanban.$('.o_progressbar a'));
    kanban.$('.o_progressbar input').focus();
    kanban.$('.o_progressbar input').val('123');
    kanban.$('.o_progressbar input').trigger($.Event('keyup', {which: $.ui.keyCode.ENTER, keyCode: $.ui.keyCode.ENTER}));
    await testUtils.nextTick();
    assert.strictEqual(kanban.$('.o_kanban_record').text().trim(), "0 / 123");
    
    kanban.destroy();
});

});
