import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    contains,
    defineActions,
    defineModels,
    fields,
    getService,
    models,
    mountWithCleanup,
    switchView,
} from "@web/../tests/web_test_helpers";
import { animationFrame } from "@odoo/hoot-mock";
import { expect, test } from "@odoo/hoot";
import { WebClient } from "@web/webclient/webclient";

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

    sequence = fields.Integer({ string: "Sequence", default: 10 });
    name = fields.Char();
    member_ids = fields.Many2many({ string: "Members", relation: "users" });
    use_opportunities = fields.Boolean({ default: true });

    _records = [
        { id: 1, name: "Mushroom Kingdom", member_ids: [1, 2] },
        { id: 2, name: "Hyrule", member_ids: [3, 4] },
    ];

    get_team_switcher_teams() {
        return this._filter([["use_opportunities", "=", true]])._records;
    }
}

class Stage extends models.Model {
    _name = "crm.stage";

    name = fields.Char();
    is_won = fields.Boolean({ string: "Is won" });
    team_ids = fields.Many2many({ relation: "crm.team" });

    _records = [
        { id: 1, name: "Start" },
        { id: 2, name: "Middle" },
        { id: 3, name: "Middle Hyrule", team_ids: [2] },
        { id: 4, name: "Won", is_won: true },
    ];
}

class Lead extends models.Model {
    _name = "crm.lead";

    name = fields.Char();
    stage_id = fields.Many2one({ string: "Stage", relation: "crm.stage" });
    team_id = fields.Many2one({ string: "Sales Team", relation: "crm.team" });
    user_id = fields.Many2one({ string: "Salesperson", relation: "users" });

    _records = [
        {
            id: 1,
            name: "Lead 1",
            stage_id: 1,
            team_id: 1,
            user_id: 1,
        },
        {
            id: 2,
            name: "Lead 2",
            stage_id: 1,
            team_id: 2,
            user_id: 2,
        },
        {
            id: 3,
            name: "Lead 3",
            stage_id: 2,
            team_id: 1,
            user_id: 3,
        },
        {
            id: 4,
            name: "Lead 4",
            stage_id: 2,
            team_id: 2,
            user_id: 4,
        },
        {
            id: 5,
            name: "Lead 5",
            stage_id: 3,
            team_id: 2,
            user_id: 1,
        },
            {
            id: 6,
            name: "Lead 6",
            stage_id: 4,
            team_id: 1,
            user_id: 4,
        },
            {
            id: 7,
            name: "Lead 7",
            stage_id: 4,
            team_id: 2,
            user_id: 2,
        },
    ];

    _views = {
        form: `
            <form>
                <group>
                    <field name="name"/>
                    <field name="team_id"/>
                </group>
            </form>
        `,
        kanban: `
            <kanban js_class="crm_kanban" default_group_by="stage_id" on_create="quick_create" quick_create_view="form">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>
        `,
        list: `
            <list js_class="crm_list">
                <field name="id"/>
                <field name="name"/>
            </list>
        `,
        search: `
            <search>
                <field name="team_id"/>
            </search>
        `,
    };
}

defineModels([Users, Team, Stage, Lead]);
defineMailModels();
defineActions([
    {
        id: 1,
        name: "Pipeline",
        res_model: "crm.lead",
        type: "ir.actions.act_window",
        context: {
            show_team_switcher: true,
        },
        views: [
            [false, "kanban"],
            [false, "list"],
            [false, "form"],
        ],
    },
]);

test.tags("desktop");
test("crm team switcher rendering", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    // Team switcher should default on first team
    expect(".o_cp_team_switcher:text('Mushroom Kingdom')").toHaveCount(1);
    // Changing the selected team should update the displayed stages and records
    // All: 7 records, 4 stages (Start, Middle, Won, Hyrule Stage)
    await contains(".o_cp_team_switcher").click();
    await contains(".o_popover .dropdown-item:text('All')").click();
    expect(".o_kanban_record").toHaveCount(7);
    expect(".o_kanban_group").toHaveCount(4);
    // Mushroom Kingdom: 3 records, 3 stages (Start, Middle, Won)
    await contains(".o_cp_team_switcher").click();
    await contains(".o_popover .dropdown-item:text('Mushroom Kingdom')").click();
    expect(".o_kanban_record").toHaveCount(3);
    expect(".o_kanban_group").toHaveCount(3);
    // Hyrule: 4 records, 4 stages (Start, Middle, Won, Hyrule Stage)
    await contains(".o_cp_team_switcher").click();
    await contains(".o_popover .dropdown-item:text('Hyrule')").click();
    expect(".o_kanban_record").toHaveCount(4);
    expect(".o_kanban_group").toHaveCount(4);
    // Selected team should be the default one on quick create (using search context)
    await contains(".o-kanban-button-new").click();
    await animationFrame();
    expect(".o_kanban_quick_create .o_field_many2one[name='team_id'] input").toHaveValue("Hyrule");
    await contains(".o_kanban_cancel").click();
    // Switching view should keep the current team selection
    await switchView("list");
    expect(".o_cp_team_switcher").toHaveText("Hyrule");
    expect("tr.o_data_row").toHaveCount(4);
    // Selected team should be the default one on record creation via form view (using action context)
    await contains(".o_list_button_add").click();
    expect(".o_field_many2one[name='team_id'] input").toHaveValue("Hyrule");
    await contains(".o_form_button_cancel").click();
});
