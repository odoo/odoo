import { expect, test } from "@odoo/hoot";
import { contains as webContains, onRpc } from "@web/../tests/web_test_helpers";
import {
    contains,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { defineCrmTeamModels } from "@sales_team/../tests/crm_team_test_helpers";

defineCrmTeamModels();

test("crm team form activate multi-team option via alert", async () => {
    expect.assertions(7);

    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Maria" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const [teamId_1] = pyEnv["crm.team"].create([
        {
            name: "Team1",
            member_ids: [userId],
        },
        {
            name: "Team2",
            member_ids: [userId],
        },
    ]);

    onRpc("has_group", ({ args }) => {
        expect.step("has_group");
        expect(args[1]).toBe("sales_team.group_sale_manager");
        return true;
    });
    onRpc("set_param", ({ args }) => {
        expect.step("set_param");
        expect(args[0]).toBe("sales_team.membership_multi");
        return true;
    });

    await start();
    await openFormView("crm.team", teamId_1, {
        arch: `<form js_class="crm_team_form">
            <field name="is_membership_multi" invisible="1"/>
            <field name="member_warning" invisible="1"/>
            <div class="alert alert-info" invisible="is_membership_multi or not member_warning">
                <field name="member_warning"/>
                Working in multiple teams?
                <button name="crm_team_activate_multi_membership" type="button">
                    Activate "Multi-team"
                </button>
            </div>
            <sheet>
                <field name="member_ids">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </sheet>
        </form>`,
    });

    // Members list should have Maria which is already in Team2 => Alert should be shown
    await expect(".o_field_widget[name='member_ids'] .o_kanban_record:visible:not(.o-kanban-button-new)").toHaveCount(1);
    await expect(".o_field_widget[name='member_ids'] .o_kanban_record:visible:not(.o-kanban-button-new)").toHaveText("Maria");
    await contains(".alert:visible", { count: 1 });

    // Clicking on the button should update the multi-team option and remove the alert
    await webContains(".alert button[name='crm_team_activate_multi_membership']").click();
    await contains(".alert:visible", { count: 0 });
    expect.verifySteps([
        "has_group",
        "set_param",
    ]);
});
