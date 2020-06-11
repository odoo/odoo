odoo.define('web_kanban_gauge.gauge_tests', function (require) {
"use strict";

const KanbanView = require('web.KanbanView');
const testUtils = require('web.test_utils');

const createView = testUtils.createView;

QUnit.module('fields', {}, function () {

QUnit.module('basic_fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    int_field: {string: "int_field", type: "integer", sortable: true},
                },
                records: [
                    {id: 1, int_field: 10},
                    {id: 2, int_field: 4},
                ]
            },
        };
    }
}, function () {

    QUnit.module('gauge widget');

    QUnit.test('basic rendering', async function (assert) {
        assert.expect(1);

        const kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: `<kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="int_field" widget="gauge"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.containsOnce(kanban, '.o_kanban_record:first .oe_gauge canvas',
            "should render the gauge widget");

        kanban.destroy();
    });

});
});
});
