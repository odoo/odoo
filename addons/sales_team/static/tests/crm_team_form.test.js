import { expect, test } from "@odoo/hoot";
import { queryFirst, waitFor } from "@odoo/hoot-dom";
import { contains as webContains, onRpc } from "@web/../tests/web_test_helpers";
import {
    contains,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { defineCrmTeamModels } from "@sales_team/../tests/crm_team_test_helpers";

defineCrmTeamModels();

const ARCH = `<form js_class="crm_team_form">
    <field name="is_membership_multi" invisible="1"/>
    <field name="member_warning" invisible="1"/>
    <div class="alert alert-info" invisible="is_membership_multi or not member_warning">
        <field name="member_warning"/>
        Working in multiple teams?
        <button name="crm_team_activate_multi_membership" type="crm_team_event">
            Activate "Multi-team"
        </button>
    </div>
    <sheet>
        <field name="name"/>
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
</form>`;

/**
 * Two teams sharing one member, so the mono-membership warning -- and with it
 * the alert carrying the button -- is displayed.
 */
async function setupSharedMember() {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Maria" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const teamIds = pyEnv["crm.team"].create([
        { name: "Team1", member_ids: [userId] },
        { name: "Team2", member_ids: [userId] },
    ]);
    return { pyEnv, teamIds };
}

test("crm team form activate multi-team option via alert", async () => {
    const { pyEnv, teamIds } = await setupSharedMember();

    // Both the group check and the parameter write live on the model. The client
    // used to guard on `user.hasGroup` without awaiting it -- an always-truthy
    // promise, so the guard never fired -- and then wrote the parameter itself,
    // which a Sales Administrator has no rights to do.
    onRpc("crm.team", "action_activate_multi_membership", ({ args }) => {
        expect.step("action_activate_multi_membership");
        expect(args).toEqual([]);
        pyEnv["crm.team"].write(teamIds, { is_membership_multi: true });
        return true;
    });

    await start();
    await openFormView("crm.team", teamIds[0], { arch: ARCH });

    // Members list should have Maria which is already in Team2 => Alert should be shown
    await expect(
        ".o_field_widget[name='member_ids'] .o_kanban_record:visible:not(.o-kanban-button-new)",
    ).toHaveText("Maria");
    await contains(".alert:visible", { count: 1 });

    // Clicking the button activates the option; the reload re-reads
    // is_membership_multi, which is what hides the alert
    await webContains(
        ".alert button[name='crm_team_activate_multi_membership']",
    ).click();
    await contains(".alert:visible", { count: 0 });
    expect.verifySteps(["action_activate_multi_membership"]);
});

test("crm team form keeps unsaved edits when activating the multi-team option", async () => {
    const { pyEnv, teamIds } = await setupSharedMember();

    onRpc("crm.team", "action_activate_multi_membership", () => {
        expect.step("action_activate_multi_membership");
        pyEnv["crm.team"].write(teamIds, { is_membership_multi: true });
        return true;
    });
    onRpc("crm.team", "web_save", () => {
        expect.step("web_save");
    });

    await start();
    await openFormView("crm.team", teamIds[0], { arch: ARCH });
    await contains(".alert:visible", { count: 1 });
    await webContains(".o_field_widget[name='name'] input").edit("Renamed draft", {
        confirm: false,
    });

    await webContains(
        ".alert button[name='crm_team_activate_multi_membership']",
    ).click();
    await contains(".alert:visible", { count: 0 });
    expect(".o_field_widget[name='name'] input").toHaveValue("Renamed draft");
    expect.verifySteps(["action_activate_multi_membership"]);
});

test("crm team form keeps the alert when activation is refused", async () => {
    const { teamIds } = await setupSharedMember();

    onRpc("crm.team", "action_activate_multi_membership", () => {
        expect.step("action_activate_multi_membership");
        throw new Error("Access Denied");
    });

    await start();
    await openFormView("crm.team", teamIds[0], { arch: ARCH });
    await contains(".alert:visible", { count: 1 });

    await webContains(
        ".alert button[name='crm_team_activate_multi_membership']",
    ).click();
    // the option is still off, so the alert must survive
    await contains(".alert:visible", { count: 1 });
    expect.verifySteps(["action_activate_multi_membership"]);

    // whatever went wrong is reported, not replaced by boilerplate. The
    // server's own AccessError is unreachable from this UI (the button lives
    // inside a group_sale_manager span, so only an administrator is ever shown
    // it); what a manager can hit is every other failure, and a fixed "an error
    // occurred" named none of them.
    await waitFor(".o_notification");
    expect(queryFirst(".o_notification_content")).toHaveText("Access Denied");
});
