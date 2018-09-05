odoo.define('sale.dashboard_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var KanbanView = require('web.KanbanView');

var createView = testUtils.createView;

QUnit.module('Sales Team Dashboard', {
    beforeEach: function () {
        this.data = {
            team: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    invoiced_target: {string: "Invoiced_target", type: "integer"},
                },
                records: [
                    {id: 1, foo: "yop"},
                ]
            },
        };
    }
});

QUnit.test('enter the value of the target', function (assert) {
    assert.expect(4);

    var kanban = createView({
        View: KanbanView,
        model: 'team',
        data: this.data,
        arch: '<kanban>' +
                '<templates>' +
                    '<t t-name="kanban-box">' +
                        '<div class="container o_kanban_card_content">' +
                            '<a href="#" class="sales_team_target_definition o_inline_link">' +
                                'Click to define a target</a>' +
                            '<div class="col-12 o_kanban_primary_bottom bottom_block">' +
                            '</div>' +
                        '</div>' +
                    '</t>' +
                '</templates>' +
              '</kanban>',
        mockRPC: function (route, args) {
            if (args.method === 'write') {
                assert.strictEqual(args.args[1]['invoiced_target'], 123, "value has updated!");
            }
            return this._super(route, args);
        },

    });
    assert.strictEqual(kanban.$('.o_kanban_view .sales_team_target_definition').length, 1,
                        "should have classname 'sales_team_target_definition'");
    assert.strictEqual(kanban.$('.o_kanban_primary_bottom.bottom_block').length, 1,
                        "should have classname 'o_kanban_primary_bottom'");

    kanban.$('a.sales_team_target_definition').click();
    assert.strictEqual(kanban.$('.o_kanban_primary_bottom.bottom_block input').length, 1,
                        "should have input element");

    kanban.$('.o_kanban_primary_bottom.bottom_block input').focus();
    kanban.$('.o_kanban_primary_bottom.bottom_block input').val('123');
    kanban.$('.o_kanban_primary_bottom.bottom_block input').blur();
    kanban.destroy();
});

});
