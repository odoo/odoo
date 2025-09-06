import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";

const now = luxon.DateTime.now();
class Users extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "Mario" },
        { id: 2, name: "Luigi" },
        { id: 3, name: "Link" },
        { id: 4, name: "Zelda" },
    ];
}

class Team extends models.Model {
    _name = "crm.team";

    name = fields.Char();
    member_ids = fields.Many2many({ string: "Members", relation: "users" });

    _records = [
        { id: 1, name: "Mushroom Kingdom", member_ids: [1, 2] },
        { id: 2, name: "Hyrule", member_ids: [3, 4] },
    ];
}

class Stage extends models.Model {
    _name = "crm.stage";

    name = fields.Char();
    is_won = fields.Boolean({ string: "Is won" });

    _records = [
        { id: 1, name: "Start" },
        { id: 2, name: "Middle" },
        { id: 3, name: "Won", is_won: true },
    ];
}

class Lead extends models.Model {
    _name = "crm.lead";

    name = fields.Char();
    planned_revenue = fields.Float({ string: "Revenue" });
    date_closed = fields.Datetime({ string: "Date closed" });
    stage_id = fields.Many2one({ string: "Stage", relation: "crm.stage" });
    user_id = fields.Many2one({ string: "Salesperson", relation: "users" });
    team_id = fields.Many2one({ string: "Sales Team", relation: "crm.team" });

    _records = [
        {
            id: 1,
            name: "Lead 1",
            planned_revenue: 5.0,
            stage_id: 1,
            team_id: 1,
            user_id: 1,
        },
        {
            id: 2,
            name: "Lead 2",
            planned_revenue: 5.0,
            stage_id: 2,
            team_id: 2,
            user_id: 4,
        },
        {
            id: 3,
            name: "Lead 3",
            planned_revenue: 3.0,
            stage_id: 3,
            team_id: 1,
            user_id: 1,
            date_closed: serializeDateTime(now.minus({ days: 5 })),
        },
        {
            id: 4,
            name: "Lead 4",
            planned_revenue: 4.0,
            stage_id: 3,
            team_id: 2,
            user_id: 4,
            date_closed: serializeDateTime(now.minus({ days: 23 })),
        },
        {
            id: 5,
            name: "Lead 5",
            planned_revenue: 7.0,
            stage_id: 3,
            team_id: 1,
            user_id: 1,
            date_closed: serializeDateTime(now.minus({ days: 20 })),
        },
        {
            id: 6,
            name: "Lead 6",
            planned_revenue: 4.0,
            stage_id: 2,
            team_id: 1,
            user_id: 2,
        },
        {
            id: 7,
            name: "Lead 7",
            planned_revenue: 1.8,
            stage_id: 3,
            team_id: 2,
            user_id: 3,
            date_closed: serializeDateTime(now.minus({ days: 23 })),
        },
        {
            id: 8,
            name: "Lead 8",
            planned_revenue: 1.9,
            stage_id: 1,
            team_id: 2,
            user_id: 3,
        },
        {
            id: 9,
            name: "Lead 9",
            planned_revenue: 1.5,
            stage_id: 3,
            team_id: 2,
            user_id: 3,
            date_closed: serializeDateTime(now.minus({ days: 5 })),
        },
        {
            id: 10,
            name: "Lead 10",
            planned_revenue: 1.7,
            stage_id: 2,
            team_id: 2,
            user_id: 3,
        },
        {
            id: 11,
            name: "Lead 11",
            planned_revenue: 2.0,
            stage_id: 3,
            team_id: 2,
            user_id: 4,
            date_closed: serializeDateTime(now.minus({ days: 5 })),
        },
    ];
}

defineModels([Lead, Users, Stage, Team]);
defineMailModels();

const testFormView = {
    arch: `
        <form js_class="crm_form">
            <header><field name="stage_id" widget="statusbar" options="{'clickable': '1'}"/></header>
            <field name="name"/>
            <field name="planned_revenue"/>
            <field name="team_id"/>
            <field name="user_id"/>
        </form>`,
    type: "form",
    resModel: "crm.lead",
};
const testKanbanView = {
    arch: `
        <kanban js_class="crm_kanban">
            <templates>
                <t t-name="card">
                    <field name="name"/>
                </t>
            </templates>
        </kanban>`,
    resModel: "crm.lead",
    type: "kanban",
    groupBy: ["stage_id"],
};

onRpc("crm.lead", "get_rainbowman_message", ({ parent }) => {
    const result = parent();
    expect.step(result || "no rainbowman");
    return result;
});

test.tags("desktop");
test("first lead won, click on statusbar on desktop", async () => {
    await mountView({
        ...testFormView,
        resId: 6,
    });

    await contains(".o_statusbar_status button[data-value='3']").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["Go, go, go! Congrats for your first deal."]);
});

test.tags("mobile");
test("first lead won, click on statusbar on mobile", async () => {
    await mountView({
        ...testFormView,
        resId: 6,
    });

    await contains(".o_statusbar_status button.dropdown-toggle").click();
    await contains(".o-dropdown--menu .dropdown-item:contains('Won')").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["Go, go, go! Congrats for your first deal."]);
});

test.tags("desktop");
test("first lead won, click on statusbar in edit mode on desktop", async () => {
    await mountView({
        ...testFormView,
        resId: 6,
    });

    await contains(".o_statusbar_status button[data-value='3']").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["Go, go, go! Congrats for your first deal."]);
});

test.tags("mobile");
test("first lead won, click on statusbar in edit mode on mobile", async () => {
    await mountView({
        ...testFormView,
        resId: 6,
    });

    await contains(".o_statusbar_status button.dropdown-toggle").click();
    await contains(".o-dropdown--menu .dropdown-item:contains('Won')").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["Go, go, go! Congrats for your first deal."]);
});

test.tags("desktop");
test("team record 30 days, click on statusbar on desktop", async () => {
    await mountView({
        ...testFormView,
        resId: 2,
    });

    await contains(".o_statusbar_status button[data-value='3']").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["Boom! Team record for the past 30 days."]);
});

test.tags("mobile");
test("team record 30 days, click on statusbar on mobile", async () => {
    await mountView({
        ...testFormView,
        resId: 2,
    });

    await contains(".o_statusbar_status button.dropdown-toggle").click();
    await contains(".o-dropdown--menu .dropdown-item:contains('Won')").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["Boom! Team record for the past 30 days."]);
});

test.tags("desktop");
test("team record 7 days, click on statusbar on desktop", async () => {
    await mountView({
        ...testFormView,
        resId: 1,
    });

    await contains(".o_statusbar_status button[data-value='3']").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["Yeah! Best deal out of the last 7 days for the team."]);
});

test.tags("mobile");
test("team record 7 days, click on statusbar on mobile", async () => {
    await mountView({
        ...testFormView,
        resId: 1,
    });

    await contains(".o_statusbar_status button.dropdown-toggle").click();
    await contains(".o-dropdown--menu .dropdown-item:contains('Won')").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["Yeah! Best deal out of the last 7 days for the team."]);
});

test.tags("desktop");
test("user record 30 days, click on statusbar on desktop", async () => {
    await mountView({
        ...testFormView,
        resId: 8,
    });

    await contains(".o_statusbar_status button[data-value='3']").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["You just beat your personal record for the past 30 days."]);
});

test.tags("mobile");
test("user record 30 days, click on statusbar on mobile", async () => {
    await mountView({
        ...testFormView,
        resId: 8,
    });

    await contains(".o_statusbar_status button.dropdown-toggle").click();
    await contains(".o-dropdown--menu .dropdown-item:contains('Won')").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["You just beat your personal record for the past 30 days."]);
});

test.tags("desktop");
test("user record 7 days, click on statusbar on desktop", async () => {
    await mountView({
        ...testFormView,
        resId: 10,
    });

    await contains(".o_statusbar_status button[data-value='3']").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["You just beat your personal record for the past 7 days."]);
});

test.tags("mobile");
test("user record 7 days, click on statusbar on mobile", async () => {
    await mountView({
        ...testFormView,
        resId: 10,
    });

    await contains(".o_statusbar_status button.dropdown-toggle").click();
    await contains(".o-dropdown--menu .dropdown-item:contains('Won')").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["You just beat your personal record for the past 7 days."]);
});

test.tags("desktop");
test("click on stage (not won) on statusbar on desktop", async () => {
    await mountView({
        ...testFormView,
        resId: 1,
    });

    await contains(".o_statusbar_status button[data-value='2']").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(0);
    expect.verifySteps(["no rainbowman"]);
});

test.tags("mobile");
test("click on stage (not won) on statusbar on mobile", async () => {
    await mountView({
        ...testFormView,
        resId: 1,
    });

    await contains(".o_statusbar_status button.dropdown-toggle").click();
    await contains(".o-dropdown--menu .dropdown-item:contains('Middle')").click();
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(0);
    expect.verifySteps(["no rainbowman"]);
});

test.tags("desktop");
test("first lead won, drag & drop kanban", async () => {
    await mountView({
        ...testKanbanView,
    });

    await contains(".o_kanban_record:contains(Lead 6):eq(0)").dragAndDrop(".o_kanban_group:eq(2)");
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["Go, go, go! Congrats for your first deal."]);
});

test.tags("desktop");
test("team record 30 days, drag & drop kanban", async () => {
    await mountView({
        ...testKanbanView,
    });

    await contains(".o_kanban_record:contains(Lead 2):eq(0)").dragAndDrop(".o_kanban_group:eq(2)");
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["Boom! Team record for the past 30 days."]);
});

test.tags("desktop");
test("team record 7 days, drag & drop kanban", async () => {
    await mountView({
        ...testKanbanView,
    });

    await contains(".o_kanban_record:contains(Lead 1):eq(0)").dragAndDrop(".o_kanban_group:eq(2)");
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["Yeah! Best deal out of the last 7 days for the team."]);
});

test.tags("desktop");
test("user record 30 days, drag & drop kanban", async () => {
    await mountView({
        ...testKanbanView,
    });

    await contains(".o_kanban_record:contains(Lead 8):eq(0)").dragAndDrop(".o_kanban_group:eq(2)");
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["You just beat your personal record for the past 30 days."]);
});

test.tags("desktop");
test("user record 7 days, drag & drop kanban", async () => {
    await mountView({
        ...testKanbanView,
    });

    await contains(".o_kanban_record:contains(Lead 10):eq(0)").dragAndDrop(".o_kanban_group:eq(2)");
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(1);
    expect.verifySteps(["You just beat your personal record for the past 7 days."]);
});

test.tags("desktop");
test("drag & drop record kanban in stage not won", async () => {
    await mountView({
        ...testKanbanView,
    });

    await contains(".o_kanban_record:contains(Lead 8):eq(0)").dragAndDrop(".o_kanban_group:eq(1)");
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(0);
    expect.verifySteps(["no rainbowman"]);
});

test.tags("desktop");
test("drag & drop record in kanban not grouped by stage_id", async () => {
    await mountView({
        ...testKanbanView,
        groupBy: ["user_id"],
    });

    await contains(".o_kanban_group:eq(0)").dragAndDrop(".o_kanban_group:eq(1)");
    expect(".o_reward svg.o_reward_rainbow_man").toHaveCount(0);
    expect.verifySteps([]); // Should never pass by the rpc
});
