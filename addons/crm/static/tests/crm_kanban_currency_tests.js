/** @odoo-module */

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { getFixture, patchWithCleanup, dragAndDrop } from "@web/../tests/helpers/utils";
import { KanbanAnimatedNumber } from "@web/views/kanban/kanban_animated_number";

let target;
let serverData;

QUnit.module('CRM Kanban Currency Tests', {
    beforeEach: function () {
        patchWithCleanup(KanbanAnimatedNumber, { enableAnimations: false });
        target = getFixture();
        setupViewRegistries();
        serverData = {
            models: {
                'res.users': {
                    fields: {
                        display_name: { string: 'Name', type: 'char' },
                    },
                    records: [
                        { id: 1, name: 'Dhvanil' },
                        { id: 2, name: 'Trivedi' },
                    ],
                },
                'crm.stage': {
                    fields: {
                        display_name: { string: 'Name', type: 'char' },
                        is_won: { string: 'Is won', type: 'boolean' },
                    },
                    records: [
                        { id: 1, name: 'New' },
                        { id: 2, name: 'Qualified' },
                        { id: 3, name: 'Won', is_won: true },
                    ],
                },
                'currency': {
                    fields: {
                        digits: { string: "Digits" },
                        symbol: {string: "Currency Sumbol", type: "char", searchable: true},
                        position: {string: "Currency Position", type: "char", searchable: true},
                    },
                    records: [{
                        id: 1,
                        display_name: "$",
                        symbol: "$",
                        position: "before",
                    }, {
                        id: 2,
                        display_name: "€",
                        symbol: "€",
                        position: "after",
                    }]
                },
                'crm.lead': {
                    fields: {
                        display_name: { string: 'Name', type: 'char' },
                        bar: {string: "Bar", type: "boolean"},
                        activity_state: {string: "Activity State", type: "char"},
                        expected_revenue: { string: 'Revenue', type: 'integer', },
                        recurring_revenue_monthly: { string: 'Recurring Revenue', type: 'integer',  sortable: true },
                        stage_id: { string: 'Stage', type: 'many2one', relation: 'crm.stage' },
                        user_id: { string: 'Salesperson', type: 'many2one', relation: 'res.users' },
                        currency_id: { string: "Currency", type: "many2one", relation: "currency", searchable: true} ,
                    },
                    records : [
                        { id: 1, bar: false, currency_id: 1, name: 'Lead 1', activity_state: 'planned', expected_revenue: 100, recurring_revenue_monthly: 5, stage_id: 1, user_id: 1 },
                        { id: 2, bar: true, currency_id: 1, name: 'Lead 2', activity_state: 'today', expected_revenue: 200, stage_id: 2, user_id: 2 },
                        { id: 3, bar: true, currency_id: 1, name: 'Lead 3', activity_state: 'planned', expected_revenue: 100, recurring_revenue_monthly: 20, stage_id: 3, user_id: 1 },
                        { id: 6, bar: true, currency_id: 2, name: 'Lead 4', activity_state: 'today', expected_revenue: 30, recurring_revenue_monthly: 15, stage_id: 1, user_id: 2 },
                    ],
                },
            },
            views: {},
        };
    },
}, function () {
    QUnit.test('kanban: currency aggregation with progressbar', async function (assert) {
        assert.expect(7);

        await makeView({
            type: "kanban",
            serverData,
            resModel: 'crm.lead',
            groupBy: ['stage_id'],
            arch: `
                <kanban js_class="crm_kanban">
                    <field name="stage_id"/>
                    <field name="expected_revenue" />
                    <field name="recurring_revenue_monthly"/>
                    <field name="activity_state"/>
                    <field name="currency_id" />
                    <progressbar field="activity_state" colors='{"planned": "success", "today": "warning", "overdue": "danger"}' sum_field="expected_revenue" recurring_revenue_sum_field="recurring_revenue_monthly"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="name"/></div>
                            <div><field name="expected_revenue" widget="monetary" options="{'currency_field': 'currency_id'}"/></div>
                        </t>
                    </templates>
                </kanban>`,
        });

        const getCounterValue = (index) => {
            return [...target.querySelectorAll('.o_kanban_counter_side')][index].textContent.trim();
        };

        // Check first group (mixed currencies)
        assert.strictEqual(
            getCounterValue(0),
            '0',
            "Should show zero when mixing currencies in group"
        );

        // Check second group (single currency)
        assert.strictEqual(
            getCounterValue(1),
            '$200',
            "Should display total for single currency group"
        );

        // Check tooltip content for mixed currency group
        const progressBar = target.querySelectorAll('.o_kanban_counter_side')[0];
        assert.strictEqual(
            progressBar.getAttribute('title'),
            'Different currencies cannot be aggregated',
            "Should show warning in tooltip for mixed currencies"
        );

        // Drag the first kanban record from 1st column to the top of the last column
        await dragAndDrop(
            [...target.querySelectorAll('.o_kanban_record')].shift(),
            [...target.querySelectorAll('.o_kanban_record')].pop(),
            { position: 'bottom' }
        );

        assert.strictEqual(
            getCounterValue(0),
            '30€',
            "Should show total when all records have same currency"
        );
        assert.strictEqual(
            getCounterValue(2),
            '$200',
            "Should show total when all records have same currency"
        );
        // Drag the first kanban record from 1st column to the top of the last column
        await dragAndDrop(
            [...target.querySelectorAll('.o_kanban_record')].shift(),
            [...target.querySelectorAll('.o_kanban_record')].pop(),
            { position: 'bottom' }
        );
        assert.strictEqual(
            getCounterValue(2),
            '0',
            "Should show zero when mixing currencies in group"
        );
        // Check tooltip content for mixed currency group
        const progressBar1 = target.querySelectorAll('.o_kanban_counter_side')[2];
        assert.strictEqual(
            progressBar1.getAttribute('title'),
            'Different currencies cannot be aggregated',
            "Should show warning in tooltip for mixed currencies"
        );
    });
});
