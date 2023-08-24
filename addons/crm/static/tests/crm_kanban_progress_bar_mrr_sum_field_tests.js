/** @odoo-module */

import { registry } from "@web/core/registry";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import {
    click,
    dragAndDrop,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
} from '@web/../tests/helpers/utils';
import { AnimatedNumber } from "@web/views/view_components/animated_number";

const serviceRegistry = registry.category("services");

let target;
let serverData;

QUnit.module('Crm Kanban Progressbar', {
    beforeEach: function () {
        patchWithCleanup(AnimatedNumber, { enableAnimations: false });
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
                'crm.lead': {
                    fields: {
                        display_name: { string: 'Name', type: 'char' },
                        bar: {string: "Bar", type: "boolean"},
                        activity_state: {string: "Activity State", type: "char"},
                        expected_revenue: { string: 'Revenue', type: 'integer', sortable: true },
                        recurring_revenue_monthly: { string: 'Recurring Revenue', type: 'integer',  sortable: true },
                        stage_id: { string: 'Stage', type: 'many2one', relation: 'crm.stage' },
                        user_id: { string: 'Salesperson', type: 'many2one', relation: 'res.users' },
                    },
                    records : [
                        { id: 1, bar: false, name: 'Lead 1', activity_state: 'planned', expected_revenue: 125, recurring_revenue_monthly: 5, stage_id: 1, user_id: 1 },
                        { id: 2, bar: true, name: 'Lead 2', activity_state: 'today', expected_revenue: 5, stage_id: 2, user_id: 2 },
                        { id: 3, bar: true, name: 'Lead 3', activity_state: 'planned', expected_revenue: 13, recurring_revenue_monthly: 20, stage_id: 3, user_id: 1 },
                        { id: 4, bar: true, name: 'Lead 4', activity_state: 'today', expected_revenue: 4, stage_id: 2, user_id: 2 },
                        { id: 5, bar: false, name: 'Lead 5', activity_state: 'overdue', expected_revenue: 8, recurring_revenue_monthly: 25, stage_id: 3, user_id: 1 },
                        { id: 6, bar: true, name: 'Lead 4', activity_state: 'today', expected_revenue: 4, recurring_revenue_monthly: 15, stage_id: 1, user_id: 2 },
                    ],
                },
            },
            views: {},
        };
        target = getFixture();
        setupViewRegistries();
        serviceRegistry.add(
            "user",
            makeFakeUserService((group) => group === "crm.group_use_recurring_revenues"),
            { force: true },
        );
    },
}, function () {
    QUnit.test("Progressbar: do not show sum of MRR if recurring revenues is not enabled", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "kanban",
            serverData,
            resModel: 'crm.lead',
            groupBy: ['stage_id'],
            arch: `
                <kanban js_class="crm_kanban">
                    <field name="stage_id"/>
                    <field name="expected_revenue"/>
                    <field name="recurring_revenue_monthly"/>
                    <field name="activity_state"/>
                    <progressbar field="activity_state" colors='{"planned": "success", "today": "warning", "overdue": "danger"}' sum_field="expected_revenue" recurring_revenue_sum_field="recurring_revenue_monthly"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="name"/></div>
                            <div><field name="recurring_revenue_monthly"/></div>
                        </t>
                    </templates>
                </kanban>`,
        });

        const reccurringRevenueNoValues = [...target.querySelectorAll('.o_crm_kanban_mrr_counter_side')].map((elem) => elem.textContent)
        assert.deepEqual(reccurringRevenueNoValues, [],
            "counter should not display recurring_revenue_monthly content");
    });

    QUnit.test("Progressbar: ensure correct MRR sum is displayed if recurring revenues is enabled", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "kanban",
            serverData,
            resModel: 'crm.lead',
            groupBy: ['stage_id'],
            arch: `
                <kanban js_class="crm_kanban">
                    <field name="stage_id"/>
                    <field name="expected_revenue"/>
                    <field name="recurring_revenue_monthly"/>
                    <field name="activity_state"/>
                    <progressbar field="activity_state" colors='{"planned": "success", "today": "warning", "overdue": "danger"}' sum_field="expected_revenue" recurring_revenue_sum_field="recurring_revenue_monthly"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="name"/></div>
                            <div><field name="recurring_revenue_monthly"/></div>
                        </t>
                    </templates>
                </kanban>`,
        });

        const reccurringRevenueValues = [...target.querySelectorAll('.o_animated_number:nth-child(3)')].map((elem) => elem.textContent);

        // When no values are given in column it should return 0 and counts value if given.
        assert.deepEqual(reccurringRevenueValues, ["+20", "+0", "+45"],
            "counter should display the sum of recurring_revenue_monthly values if values are given else display 0");
    });

    QUnit.test("Progressbar: ensure correct MRR updation after state change", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "kanban",
            serverData,
            resModel: 'crm.lead',
            groupBy: ['bar'],
            arch: `
                <kanban js_class="crm_kanban">
                    <field name="stage_id"/>
                    <field name="expected_revenue"/>
                    <field name="recurring_revenue_monthly"/>
                    <field name="activity_state"/>
                    <progressbar field="activity_state" colors='{"planned": "success", "today": "warning", "overdue": "danger"}' sum_field="expected_revenue" recurring_revenue_sum_field="recurring_revenue_monthly"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="name"/></div>
                            <div><field name="expected_revenue"/></div>
                            <div><field name="recurring_revenue_monthly"/></div>
                        </t>
                    </templates>
                </kanban>`,
        });

        //MRR before state change
        let reccurringRevenueNoValues = [...target.querySelectorAll('.o_animated_number:nth-child(3)')].map((elem) => elem.textContent);
        assert.deepEqual(reccurringRevenueNoValues, ['+30','+35'],
            "counter should display the sum of recurring_revenue_monthly values");

        // Drag the first kanban record from 1st column to the top of the last column
        await dragAndDrop(
            [...target.querySelectorAll('.o_kanban_record')].shift(),
            [...target.querySelectorAll('.o_kanban_record')].pop(),
            { position: 'bottom' }
        );

        //check MRR after drag&drop
        reccurringRevenueNoValues = [...target.querySelectorAll('.o_animated_number:nth-child(3)')].map((elem) => elem.textContent);
        assert.deepEqual(reccurringRevenueNoValues, ['+25', '+40'],
        "counter should display the sum of recurring_revenue_monthly correctly after drag and drop");

        //Activate "planned" filter on first column
        await click(target.querySelector('.o_kanban_group:nth-child(2) .progress-bar[aria-valuenow="2"]'), null);

        //check MRR after applying filter
        reccurringRevenueNoValues = [...target.querySelectorAll('.o_animated_number:nth-child(3)')].map((elem) => elem.textContent);
        assert.deepEqual(reccurringRevenueNoValues, ['+25','+25'],
            "counter should display the sum of recurring_revenue_monthly only of overdue filter in 1st column");
    });

    QUnit.test("Quickly drag&drop records when grouped by stage_id", async function (assert) {

        const def = makeDeferred();
        await makeView({
            type: "kanban",
            serverData,
            resModel: 'crm.lead',
            groupBy: ['stage_id'],
            arch: `
                <kanban js_class="crm_kanban">
                    <field name="stage_id"/>
                    <field name="expected_revenue"/>
                    <field name="recurring_revenue_monthly"/>
                    <field name="activity_state"/>
                    <progressbar field="activity_state" colors='{"planned": "success", "today": "warning", "overdue": "danger"}' sum_field="expected_revenue" recurring_revenue_sum_field="recurring_revenue_monthly"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="name"/></div>
                            <div><field name="expected_revenue"/></div>
                            <div><field name="recurring_revenue_monthly"/></div>
                        </t>
                    </templates>
                </kanban>`,
            async mockRPC(route, args) {
                if (args.method === "web_save") {
                    await def;
                }
            }
        });

        assert.containsN(target, ".o_kanban_group", 3);
        assert.containsN(target.querySelectorAll(".o_kanban_group")[0], ".o_kanban_record", 2);
        assert.containsN(target.querySelectorAll(".o_kanban_group")[1], ".o_kanban_record", 2);
        assert.containsN(target.querySelectorAll(".o_kanban_group")[2], ".o_kanban_record", 2);

        // drag the first record of the first column on top of the second column
        await dragAndDrop(
            target.querySelectorAll('.o_kanban_group')[0].querySelector('.o_kanban_record'),
            target.querySelectorAll('.o_kanban_group')[1].querySelector('.o_kanban_record'),
            { position: 'top' }
        );

        assert.containsOnce(target.querySelectorAll(".o_kanban_group")[0], ".o_kanban_record");
        assert.containsN(target.querySelectorAll(".o_kanban_group")[1], ".o_kanban_record", 3);
        assert.containsN(target.querySelectorAll(".o_kanban_group")[2], ".o_kanban_record", 2);

        // drag that same record to the third column -> should have no effect as save still pending
        // (but mostly, should not crash)
        await dragAndDrop(
            target.querySelectorAll('.o_kanban_group')[1].querySelector('.o_kanban_record'),
            target.querySelectorAll('.o_kanban_group')[2].querySelector('.o_kanban_record'),
            { position: 'top' }
        );

        assert.containsOnce(target.querySelectorAll(".o_kanban_group")[0], ".o_kanban_record");
        assert.containsN(target.querySelectorAll(".o_kanban_group")[1], ".o_kanban_record", 3);
        assert.containsN(target.querySelectorAll(".o_kanban_group")[2], ".o_kanban_record", 2);

        def.resolve();
        await nextTick();

        // drag that same record to the third column
        await dragAndDrop(
            target.querySelectorAll('.o_kanban_group')[1].querySelector('.o_kanban_record'),
            target.querySelectorAll('.o_kanban_group')[2].querySelector('.o_kanban_record'),
            { position: 'top' }
        );

        assert.containsOnce(target.querySelectorAll(".o_kanban_group")[0], ".o_kanban_record");
        assert.containsN(target.querySelectorAll(".o_kanban_group")[1], ".o_kanban_record", 2);
        assert.containsN(target.querySelectorAll(".o_kanban_group")[2], ".o_kanban_record", 3);
    });
});
