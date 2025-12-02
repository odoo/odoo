import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred, queryAllTexts } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";
import { AnimatedNumber } from "@web/views/view_components/animated_number";

class Users extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "Dhvanil" },
        { id: 2, name: "Trivedi" },
    ];
}

class Stage extends models.Model {
    _name = "crm.stage";

    name = fields.Char();
    is_won = fields.Boolean({ string: "Is won" });

    _records = [
        { id: 1, name: "New" },
        { id: 2, name: "Qualified" },
        { id: 3, name: "Won", is_won: true },
    ];
}

class Lead extends models.Model {
    _name = "crm.lead";

    name = fields.Char();
    bar = fields.Boolean();
    activity_state = fields.Char({ string: "Activity State" });
    expected_revenue = fields.Integer({ string: "Revenue", sortable: true, aggregator: "sum" });
    recurring_revenue_monthly = fields.Integer({
        string: "Recurring Revenue",
        sortable: true,
        aggregator: "sum",
    });
    stage_id = fields.Many2one({ string: "Stage", relation: "crm.stage" });
    user_id = fields.Many2one({ string: "Salesperson", relation: "users" });

    _records = [
        {
            id: 1,
            bar: false,
            name: "Lead 1",
            activity_state: "planned",
            expected_revenue: 125,
            recurring_revenue_monthly: 5,
            stage_id: 1,
            user_id: 1,
        },
        {
            id: 2,
            bar: true,
            name: "Lead 2",
            activity_state: "today",
            expected_revenue: 5,
            stage_id: 2,
            user_id: 2,
        },
        {
            id: 3,
            bar: true,
            name: "Lead 3",
            activity_state: "planned",
            expected_revenue: 13,
            recurring_revenue_monthly: 20,
            stage_id: 3,
            user_id: 1,
        },
        {
            id: 4,
            bar: true,
            name: "Lead 4",
            activity_state: "today",
            expected_revenue: 4,
            stage_id: 2,
            user_id: 2,
        },
        {
            id: 5,
            bar: false,
            name: "Lead 5",
            activity_state: "overdue",
            expected_revenue: 8,
            recurring_revenue_monthly: 25,
            stage_id: 3,
            user_id: 1,
        },
        {
            id: 6,
            bar: true,
            name: "Lead 4",
            activity_state: "today",
            expected_revenue: 4,
            recurring_revenue_monthly: 15,
            stage_id: 1,
            user_id: 2,
        },
    ];
}

defineModels([Lead, Users, Stage]);
defineMailModels();
beforeEach(() => {
    patchWithCleanup(AnimatedNumber, { enableAnimations: false });
    patchWithCleanup(user, { hasGroup: (group) => group === "crm.group_use_recurring_revenues" });
});
test("Progressbar: do not show sum of MRR if recurring revenues is not enabled", async () => {
    patchWithCleanup(user, { hasGroup: () => false });
    await mountView({
        type: "kanban",
        resModel: "crm.lead",
        groupBy: ["stage_id"],
        arch: `
                <kanban js_class="crm_kanban">
                    <field name="activity_state"/>
                    <progressbar field="activity_state" colors='{"planned": "success", "today": "warning", "overdue": "danger"}' sum_field="expected_revenue" recurring_revenue_sum_field="recurring_revenue_monthly"/>
                    <templates>
                        <t t-name="card" class="flex-row justify-content-between">
                            <field name="name" class="p-2"/>
                            <field name="recurring_revenue_monthly" class="p-2"/>
                        </t>
                    </templates>
                </kanban>`,
    });

    expect(queryAllTexts(".o_kanban_counter")).toEqual(["129", "9", "21"], {
        message: "counter should not display recurring_revenue_monthly content",
    });
});

test("Progressbar: ensure correct MRR sum is displayed if recurring revenues is enabled", async () => {
    await mountView({
        type: "kanban",
        resModel: "crm.lead",
        groupBy: ["stage_id"],
        arch: `
                <kanban js_class="crm_kanban">
                    <field name="activity_state"/>
                    <progressbar field="activity_state" colors='{"planned": "success", "today": "warning", "overdue": "danger"}' sum_field="expected_revenue" recurring_revenue_sum_field="recurring_revenue_monthly"/>
                    <templates>
                        <t t-name="card" class="flex-row justify-content-between">
                            <field name="name" class="p-2"/>
                            <field name="recurring_revenue_monthly" class="p-2"/>
                        </t>
                    </templates>
                </kanban>`,
    });

    // When no values are given in column it should return 0 and counts value if given
    // MRR=0 shouldn't be displayed, however.
    expect(queryAllTexts(".o_kanban_counter")).toEqual(["129\n+20", "9", "21\n+45"], {
        message: "counter should display the sum of recurring_revenue_monthly values",
    });
});

test.tags("desktop");
test("Progressbar: ensure correct MRR updation after state change", async () => {
    await mountView({
        type: "kanban",
        resModel: "crm.lead",
        groupBy: ["bar"],
        arch: `
                <kanban js_class="crm_kanban">
                    <field name="activity_state"/>
                    <progressbar field="activity_state" colors='{"planned": "success", "today": "warning", "overdue": "danger"}' sum_field="expected_revenue" recurring_revenue_sum_field="recurring_revenue_monthly"/>
                    <templates>
                        <t t-name="card" class="flex-row justify-content-between">
                            <field name="name" class="p-2"/>
                            <field name="expected_revenue" class="p-2"/>
                            <field name="recurring_revenue_monthly" class="p-2"/>
                        </t>
                    </templates>
                </kanban>`,
    });

    //MRR before state change
    expect(queryAllTexts(".o_animated_number[data-tooltip='Recurring Revenue']")).toEqual(
        ["+30", "+35"],
        {
            message: "counter should display the sum of recurring_revenue_monthly values",
        }
    );

    // Drag the first kanban record from 1st column to the top of the last column
    await contains(".o_kanban_record:first").dragAndDrop(".o_kanban_record:last");

    //check MRR after drag&drop
    expect(queryAllTexts(".o_animated_number[data-tooltip='Recurring Revenue']")).toEqual(
        ["+25", "+40"],
        {
            message:
                "counter should display the sum of recurring_revenue_monthly correctly after drag and drop",
        }
    );

    //Activate "planned" filter on first column
    await contains('.o_kanban_group:eq(1) .progress-bar[aria-valuenow="2"]').click();

    //check MRR after applying filter
    expect(queryAllTexts(".o_animated_number[data-tooltip='Recurring Revenue']")).toEqual(
        ["+25", "+25"],
        {
            message:
                "counter should display the sum of recurring_revenue_monthly only of overdue filter in 1st column",
        }
    );
});

test.tags("desktop");
test("Quickly drag&drop records when grouped by stage_id", async () => {
    const def = new Deferred();
    await mountView({
        type: "kanban",
        resModel: "crm.lead",
        groupBy: ["stage_id"],
        arch: `
                <kanban js_class="crm_kanban">
                    <field name="activity_state"/>
                    <progressbar field="activity_state" colors='{"planned": "success", "today": "warning", "overdue": "danger"}' sum_field="expected_revenue" recurring_revenue_sum_field="recurring_revenue_monthly"/>
                    <templates>
                        <t t-name="card" class="flex-row justify-content-between">
                            <field name="name" class="p-2"/>
                            <field name="expected_revenue" class="p-2"/>
                            <field name="recurring_revenue_monthly" class="p-2"/>
                        </t>
                    </templates>
                </kanban>`,
    });
    onRpc("web_save", async () => {
        await def;
    });

    expect(".o_kanban_group").toHaveCount(3);
    expect(".o_kanban_group:eq(0) .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:eq(1) .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:eq(2) .o_kanban_record").toHaveCount(2);

    // drag the first record of the first column on top of the second column
    await contains(".o_kanban_group:eq(0) .o_kanban_record").dragAndDrop(
        ".o_kanban_group:eq(1) .o_kanban_record"
    );

    expect(".o_kanban_group:eq(0) .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:eq(1) .o_kanban_record").toHaveCount(3);
    expect(".o_kanban_group:eq(2) .o_kanban_record").toHaveCount(2);

    // drag that same record to the third column -> should have no effect as save still pending
    // (but mostly, should not crash)
    await contains(".o_kanban_group:eq(1) .o_kanban_record").dragAndDrop(
        ".o_kanban_group:eq(2) .o_kanban_record"
    );

    expect(".o_kanban_group:eq(0) .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:eq(1) .o_kanban_record").toHaveCount(3);
    expect(".o_kanban_group:eq(2) .o_kanban_record").toHaveCount(2);

    def.resolve();
    await animationFrame();

    // drag that same record to the third column
    await contains(".o_kanban_group:eq(1) .o_kanban_record").dragAndDrop(
        ".o_kanban_group:eq(2) .o_kanban_record"
    );

    expect(".o_kanban_group:eq(0) .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:eq(1) .o_kanban_record").toHaveCount(2);
    expect(".o_kanban_group:eq(2) .o_kanban_record").toHaveCount(3);
});
