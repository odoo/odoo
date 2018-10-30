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

QUnit.test('edit target with several o_kanban_primary_bottom divs', function (assert) {
    assert.expect(4);

    var kanban = createView({
        View: KanbanView,
        model: 'crm.team',
        data: this.data,
        arch: '<kanban>' +
                '<templates>' +
                    '<t t-name="kanban-box">' +
                        '<div class="container o_kanban_card_content">' +
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
            return this._super.apply(this, arguments);
        },

    });

    assert.strictEqual(kanban.$('.o_kanban_view .sales_team_target_definition').length, 1,
        "should have classname 'sales_team_target_definition'");
    assert.strictEqual(kanban.$('.o_kanban_primary_bottom').length, 2,
        "should have two divs with classname 'o_kanban_primary_bottom'");

    kanban.$('a.sales_team_target_definition').click();
    assert.strictEqual(kanban.$('.o_kanban_primary_bottom:last input').length, 1,
        "should have rendered an input in the last o_kanban_primary_bottom div");

    kanban.$('.o_kanban_primary_bottom:last input').focus();
    kanban.$('.o_kanban_primary_bottom:last input').val('123');
    kanban.$('.o_kanban_primary_bottom:last input').blur();

    kanban.destroy();
});

});
