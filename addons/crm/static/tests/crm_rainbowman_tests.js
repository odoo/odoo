import "@crm/../tests/mock_server";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import {
    click,
    dragAndDrop,
    getFixture,
} from '@web/../tests/helpers/utils';
import { serializeDateTime } from "@web/core/l10n/dates";

let target;

function getMockRpc(assert) {
    return async (route, args, performRpc) => {
        const result = await performRpc(route, args);
        if (args.model === 'crm.lead' && args.method === 'get_rainbowman_message') {
            assert.step(result || "no rainbowman");
        }
        return result;
    };
}

QUnit.module('Crm Rainbowman Triggers', {
    beforeEach: function () {
        const now = luxon.DateTime.now();
        const serverData = {
            models: {
                'res.users': {
                    fields: {
                        display_name: { string: 'Name', type: 'char' },
                    },
                    records: [
                        { id: 1, name: 'Mario' },
                        { id: 2, name: 'Luigi' },
                        { id: 3, name: 'Link' },
                        { id: 4, name: 'Zelda' },
                    ],
                },
                'crm.team': {
                    fields: {
                        display_name: { string: 'Name', type: 'char' },
                        member_ids: { string: 'Members', type: 'many2many', relation: 'res.users' },
                    },
                    records: [
                        { id: 1, name: 'Mushroom Kingdom', member_ids: [1, 2] },
                        { id: 2, name: 'Hyrule', member_ids: [3, 4] },
                    ],
                },
                'crm.stage': {
                    fields: {
                        display_name: { string: 'Name', type: 'char' },
                        is_won: { string: 'Is won', type: 'boolean' },
                    },
                    records: [
                        { id: 1, name: 'Start' },
                        { id: 2, name: 'Middle' },
                        { id: 3, name: 'Won', is_won: true},
                    ],
                },
                'crm.lead': {
                    fields: {
                        display_name: { string: 'Name', type: 'char' },
                        planned_revenue: { string: 'Revenue', type: 'float' },
                        stage_id: { string: 'Stage', type: 'many2one', relation: 'crm.stage' },
                        team_id: { string: 'Sales Team', type: 'many2one', relation: 'crm.team' },
                        user_id: { string: 'Salesperson', type: 'many2one', relation: 'res.users' },
                        date_closed: { string: 'Date closed', type: 'datetime' },
                    },
                    records : [
                        { id: 1, name: 'Lead 1', planned_revenue: 5.0, stage_id: 1, team_id: 1, user_id: 1 },
                        { id: 2, name: 'Lead 2', planned_revenue: 5.0, stage_id: 2, team_id: 2, user_id: 4 },
                        { id: 3, name: 'Lead 3', planned_revenue: 3.0, stage_id: 3, team_id: 1, user_id: 1, date_closed: serializeDateTime(now.minus({days: 5})) },
                        { id: 4, name: 'Lead 4', planned_revenue: 4.0, stage_id: 3, team_id: 2, user_id: 4, date_closed: serializeDateTime(now.minus({days: 23})) },
                        { id: 5, name: 'Lead 5', planned_revenue: 7.0, stage_id: 3, team_id: 1, user_id: 1, date_closed: serializeDateTime(now.minus({days: 20})) },
                        { id: 6, name: 'Lead 6', planned_revenue: 4.0, stage_id: 2, team_id: 1, user_id: 2 },
                        { id: 7, name: 'Lead 7', planned_revenue: 1.8, stage_id: 3, team_id: 2, user_id: 3, date_closed: serializeDateTime(now.minus({days: 23})) },
                        { id: 8, name: 'Lead 8', planned_revenue: 1.9, stage_id: 1, team_id: 2, user_id: 3 },
                        { id: 9, name: 'Lead 9', planned_revenue: 1.5, stage_id: 3, team_id: 2, user_id: 3, date_closed: serializeDateTime(now.minus({days: 5})) },
                        { id: 10, name: 'Lead 10', planned_revenue: 1.7, stage_id: 2, team_id: 2, user_id: 3 },
                        { id: 11, name: 'Lead 11', planned_revenue: 2.0, stage_id: 3, team_id: 2, user_id: 4, date_closed: serializeDateTime(now.minus({days: 5})) },
                    ],
                },
            },
            views: {},
        };
        this.testFormView = {
            arch: `
                <form js_class="crm_form">
                    <header><field name="stage_id" widget="statusbar" options="{'clickable': '1'}"/></header>
                    <field name="name"/>
                    <field name="planned_revenue"/>
                    <field name="team_id"/>
                    <field name="user_id"/>
                </form>`,
            serverData,
            type: "form",
            resModel: 'crm.lead',
        };
        this.testKanbanView = {
            arch: `
                <kanban js_class="crm_kanban">
                    <templates>
                        <t t-name="card">
                            <field name="name"/>
                        </t>
                    </templates>
                </kanban>`,
            serverData,
            resModel: 'crm.lead',
            type: "kanban",
            groupBy: ['stage_id'],
        };
        target = getFixture();
        setupViewRegistries();
    },
}, function () {
    QUnit.test("first lead won, click on statusbar", async function (assert) {
        assert.expect(2);

        await makeView({
            ...this.testFormView,
            resId: 6,
            mockRPC: getMockRpc(assert),
        });

        await click(target.querySelector(".o_statusbar_status button[data-value='3']"));
        assert.verifySteps(['Go, go, go! Congrats for your first deal.']);
    });

    QUnit.test("first lead won, click on statusbar in edit mode", async function (assert) {
        assert.expect(2);

        await makeView({
            ...this.testFormView,
            resId: 6,
            mockRPC: getMockRpc(assert),
        });

        await click(target.querySelector(".o_statusbar_status button[data-value='3']"));
        assert.verifySteps(['Go, go, go! Congrats for your first deal.']);
    });

    QUnit.test("team record 30 days, click on statusbar", async function (assert) {
        assert.expect(2);

        await makeView({
            ...this.testFormView,
            resId: 2,
            mockRPC: getMockRpc(assert),
        });

        await click(target.querySelector(".o_statusbar_status button[data-value='3']"));
        assert.verifySteps(['Boom! Team record for the past 30 days.']);
    });

    QUnit.test("team record 7 days, click on statusbar", async function (assert) {
        assert.expect(2);

        await makeView({
            ...this.testFormView,
            resId: 1,
            mockRPC: getMockRpc(assert),
        });

        await click(target.querySelector(".o_statusbar_status button[data-value='3']"));
        assert.verifySteps(['Yeah! Deal of the last 7 days for the team.']);
    });

    QUnit.test("user record 30 days, click on statusbar", async function (assert) {
        assert.expect(2);

        await makeView({
            ...this.testFormView,
            resId: 8,
            mockRPC: getMockRpc(assert),
        });

        await click(target.querySelector(".o_statusbar_status button[data-value='3']"));
        assert.verifySteps(['You just beat your personal record for the past 30 days.']);
    });

    QUnit.test("user record 7 days, click on statusbar", async function (assert) {
        assert.expect(2);

        await makeView({
            ...this.testFormView,
            resId: 10,
            mockRPC: getMockRpc(assert),
        });

        await click(target.querySelector(".o_statusbar_status button[data-value='3']"));
        assert.verifySteps(['You just beat your personal record for the past 7 days.']);
    });

    QUnit.test("click on stage (not won) on statusbar", async function (assert) {
        assert.expect(2);

        await makeView({
            ...this.testFormView,
            resId: 1,
            mockRPC: getMockRpc(assert),
        });

        await click(target.querySelector(".o_statusbar_status button[data-value='2']"));
        assert.verifySteps(['no rainbowman']);
    });

    QUnit.test("first lead won, drag & drop kanban", async function (assert) {
        assert.expect(2);

        await makeView({
            ...this.testKanbanView,
            mockRPC: getMockRpc(assert),
        });

        await dragAndDrop($(target).find(".o_kanban_record:contains(Lead 6)")[0], target.querySelector('.o_kanban_group:nth-of-type(3)'));
        assert.verifySteps(['Go, go, go! Congrats for your first deal.']);
    });

    QUnit.test("team record 30 days, drag & drop kanban", async function (assert) {
        assert.expect(2);

        await makeView({
            ...this.testKanbanView,
            mockRPC: getMockRpc(assert),
        });

        await dragAndDrop($(target).find(".o_kanban_record:contains(Lead 2)")[0], target.querySelector('.o_kanban_group:nth-of-type(3)'));
        assert.verifySteps(['Boom! Team record for the past 30 days.']);
    });

    QUnit.test("team record 7 days, drag & drop kanban", async function (assert) {
        assert.expect(2);

        await makeView({
            ...this.testKanbanView,
            mockRPC: getMockRpc(assert),
        });

        await dragAndDrop($(target).find(".o_kanban_record:contains(Lead 1)")[0], target.querySelector('.o_kanban_group:nth-of-type(3)'));
        assert.verifySteps(['Yeah! Deal of the last 7 days for the team.']);
    });

    QUnit.test("user record 30 days, drag & drop kanban", async function (assert) {
        assert.expect(2);

        await makeView({
            ...this.testKanbanView,
            mockRPC: getMockRpc(assert),
        });

        await dragAndDrop($(target).find(".o_kanban_record:contains(Lead 8)")[0], target.querySelector('.o_kanban_group:nth-of-type(3)'));
        assert.verifySteps(['You just beat your personal record for the past 30 days.']);
    });

    QUnit.test("user record 7 days, drag & drop kanban", async function (assert) {
        assert.expect(2);

        await makeView({
            ...this.testKanbanView,
            mockRPC: getMockRpc(assert),
        });

        await dragAndDrop($(target).find(".o_kanban_record:contains(Lead 10)")[0], target.querySelector('.o_kanban_group:nth-of-type(3)'));
        assert.verifySteps(['You just beat your personal record for the past 7 days.']);
    });

    QUnit.test("drag & drop record kanban in stage not won", async function (assert) {
        assert.expect(2);

        await makeView({
            ...this.testKanbanView,
            mockRPC: getMockRpc(assert),
        });

        await dragAndDrop($(target).find(".o_kanban_record:contains(Lead 8)")[0], target.querySelector('.o_kanban_group:nth-of-type(2)'));
        assert.verifySteps(["no rainbowman"]);
    });

    QUnit.test("drag & drop record in kanban not grouped by stage_id", async function (assert) {
        assert.expect(1);

        await makeView({
            ...this.testKanbanView,
            groupBy: ["user_id"],
            mockRPC: getMockRpc(assert),
        });

        await dragAndDrop(target.querySelector('.o_kanban_group:nth-of-type(1)'), target.querySelector('.o_kanban_group:nth-of-type(2)'));
        assert.verifySteps([]); // Should never pass by the rpc
    });
});
