import { describe, expect, test } from "@odoo/hoot";
import { click, edit } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { AccountAnalyticAccount } from "@analytic/../tests/mock_server/mock_models/account_analytic_account";
import { contains, mountView } from "@web/../tests/web_test_helpers";

import { defineTimesheetModels, ProjectProject } from "./hr_timesheet_models";

defineTimesheetModels();
describe.current.tags("desktop");

test("project.project (form): removing the analytic account requires confirmation on save", async () => {
    AccountAnalyticAccount._records = [{ id: 101, name: "Test Analytic Account" }];
    ProjectProject._records = [
        { id: 1, name: "Project 1", allow_timesheets: true, account_id: 101 },
    ];

    await mountView({
        resModel: "project.project",
        resId: 1,
        type: "form",
        arch: `
            <form js_class="project_project_form">
                <group>
                    <field name="name"/>
                    <field name="account_id"/>
                    <field name="allow_timesheets"/>
                </group>
            </form>`,
    });

    expect('.o_field_widget[name="allow_timesheets"] input[type="checkbox"]').toBeChecked();
    expect('.o_field_widget[name="account_id"] input').toHaveValue("Test Analytic Account");

    await click('.o_field_widget[name="account_id"] input');
    await edit("");
    await click('.o_field_widget[name="name"] input');

    expect('.o_field_widget[name="account_id"] input').toHaveValue("");
    expect('.o_field_widget[name="allow_timesheets"] input[type="checkbox"]').toBeChecked();

    await contains(".o_form_button_save").click();

    await contains(".o_dialog .btn-primary").click();
    await animationFrame();

    expect('.o_field_widget[name="account_id"] input').toHaveValue("");
});
