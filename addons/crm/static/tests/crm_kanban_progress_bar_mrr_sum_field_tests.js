/** @odoo-module */
import CrmKanban from '../src/js/crm_kanban';
import KanbanColumnProgressBar from 'web.KanbanColumnProgressBar';
import testUtils from 'web.test_utils';

const createView = testUtils.createView;
const CrmKanbanView = CrmKanban.CrmKanbanView;

QUnit.module('Crm Kanban Progressbar', {
    before: function () {
        this._initialKanbanProgressBarAnimate = KanbanColumnProgressBar.prototype.ANIMATE;
        KanbanColumnProgressBar.prototype.ANIMATE = false;
    },
    after: function () {
        KanbanColumnProgressBar.prototype.ANIMATE = this._initialKanbanProgressBarAnimate;
    },
    beforeEach: function () {
        this.data = {
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
                },
                records: [
                    { id: 1, name: 'New' },
                    { id: 2, name: 'Qualified' },
                    { id: 3, name: 'Won' },
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
        };
    },
}, function () {
    QUnit.test("Progressbar: do not show sum of MRR if recurring revenues is not enabled", async function (assert) {
        assert.expect(1);

        const kanban = await createView({
            data: this.data,
            model: 'crm.lead',
            View: CrmKanbanView,
            groupBy: ['stage_id'],
            session: {
                async user_has_group(group) {
                    if (group === 'crm.group_use_recurring_revenues') {
                        return false;
                    }
                    return this._super(...arguments);
                },
            },
            arch: `
                <kanban js_class="crm_kanban">
                    '<field name="stage_id"/>' +
                    '<field name="expected_revenue"/>' +
                    '<field name="recurring_revenue_monthly"/>' +
                    '<field name="activity_state"/>' +
                    <progressbar field="activity_state" colors='{"planned": "success", "today": "warning", "overdue": "danger"}' sum_field="expected_revenue" recurring_revenue_sum_field="recurring_revenue_monthly"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="name"/></div>
                            <div><field name="recurring_revenue_monthly"/></div>
                        </t>
                    </templates>
                </kanban>`,
        });

        const reccurringRevenueNoValues = [...kanban.el.querySelectorAll('.o_crm_kanban_mrr_counter_side')].map((elem) => elem.textContent)
        assert.deepEqual(reccurringRevenueNoValues, [],
            "counter should not display recurring_revenue_monthly content");
        kanban.destroy();
    });

    QUnit.test("Progressbar: ensure correct MRR sum is displayed if recurring revenues is enabled", async function (assert) {
        assert.expect(1);

        const kanban = await createView({
            data: this.data,
            model: 'crm.lead',
            View: CrmKanbanView,
            groupBy: ['stage_id'],
            session: {
                async user_has_group(group) {
                    if (group === 'crm.group_use_recurring_revenues') {
                        return true;
                    }
                    return this._super(...arguments);
                },
            },
            arch: `
                <kanban js_class="crm_kanban">
                    '<field name="stage_id"/>' +
                    '<field name="expected_revenue"/>' +
                    '<field name="recurring_revenue_monthly"/>' +
                    '<field name="activity_state"/>' +
                    <progressbar field="activity_state" colors='{"planned": "success", "today": "warning", "overdue": "danger"}' sum_field="expected_revenue" recurring_revenue_sum_field="recurring_revenue_monthly"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="name"/></div>
                            <div><field name="recurring_revenue_monthly"/></div>
                        </t>
                    </templates>
                </kanban>`,
        });

        const reccurringRevenueValues = [...kanban.el.querySelectorAll('.o_crm_kanban_mrr_sum')].map((elem) => elem.textContent);

        // When no values are given in column it should return 0 and counts value if given.
        assert.deepEqual(reccurringRevenueValues, ["20", "0", "45"],
            "counter should display the sum of recurring_revenue_monthly values if values are given else display 0");
        kanban.destroy();
    });

    QUnit.test("Progressbar: ensure correct MRR updation after state change", async function (assert) {
        assert.expect(3);

        const kanban = await createView({
            data: this.data,
            model: 'crm.lead',
            View: CrmKanbanView,
            groupBy: ['bar'],
            session: {
                async user_has_group(group) {
                    if (group === 'crm.group_use_recurring_revenues') {
                        return true;
                    }
                    return this._super(...arguments);
                },
            },
            arch: `
                <kanban js_class="crm_kanban">
                    '<field name="stage_id"/>' +
                    '<field name="expected_revenue"/>' +
                    '<field name="recurring_revenue_monthly"/>' +
                    '<field name="activity_state"/>' +
                    <progressbar field="activity_state" colors='{"planned": "success", "today": "warning", "overdue": "danger"}' sum_field="expected_revenue" recurring_revenue_sum_field="recurring_revenue_monthly"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="name"/></div>
                            <div><field name="recurring_revenue_monthly"/></div>
                        </t>
                    </templates>
                </kanban>`,
        });

        //MRR before state change
        let reccurringRevenueNoValues = [...kanban.el.querySelectorAll('.o_crm_kanban_mrr_sum')].map((elem) => elem.textContent);
        assert.deepEqual(reccurringRevenueNoValues, ['30','35'],
            "counter should display the sum of recurring_revenue_monthly values");

        // Drag the first kanban record from 1st column to the top of the last column
        await testUtils.dom.dragAndDrop(
            [...kanban.el.querySelectorAll('.o_kanban_record')].shift(),
            [...kanban.el.querySelectorAll('.o_kanban_record')].pop(),
            { position: 'bottom' }
        );

        //check MRR after drag&drop
        reccurringRevenueNoValues = [...kanban.el.querySelectorAll('.o_crm_kanban_mrr_sum')].map((elem) => elem.textContent)
        assert.deepEqual(reccurringRevenueNoValues, ['25', '40'],
            "counter should display the sum of recurring_revenue_monthly correctly after drag and drop");

        //Activate "planned" filter on first column
        await testUtils.dom.click(kanban.el.querySelector('.o_kanban_group:nth-child(2) .progress-bar[data-filter="planned"]'));

        //check MRR after applying filter
        reccurringRevenueNoValues = [...kanban.el.querySelectorAll('.o_crm_kanban_mrr_sum')].map((elem) => elem.textContent);
        assert.deepEqual(reccurringRevenueNoValues, ['25','25'],
            "counter should display the sum of recurring_revenue_monthly only of overdue filter in 1st column");
        kanban.destroy();
    });
});
