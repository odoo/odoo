import { test, expect, beforeEach, animationFrame } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { startServer } from "@mail/../tests/mail_test_helpers";
import { mountView, contains } from "@web/../tests/web_test_helpers";
import { defineTimesheetModels } from "./hr_timesheet_models";

defineTimesheetModels();

let pyEnv;
beforeEach(async () => {
    pyEnv = await startServer();
    pyEnv["account.analytic.line"].unlink(pyEnv["account.analytic.line"].search([]));
});

test.tags("desktop");
test("hr.timesheet (list): when timesheet's with different projects are selected task & project can't be modified ", async () => {
    pyEnv["account.analytic.line"].create([
        {
            project_id: 1,
            task_id: 3,
            unit_amount: 1,
        },
        {
            project_id: false,
            task_id: false,
            unit_amount: 2,
        },
    ]);

    await mountView({
        type: "list",
        resModel: "account.analytic.line",
        arch: `
            <list multi_edit="1" js_class="timesheet_list_view">
                <field name="project_id"/>
                <field name="task_id"/>
                <field name="name"/>
            </list>
        `,
    });
    // Select all rows
    await contains(`.o_list_record_selector`).click();

    // // Verify that bulk editing of timesheet names is permitted
    await contains("tbody > tr:first-child > td[name='name']").click();
    await contains("tbody > tr:first-child > td[name='name'] input").edit("Sample Text");
    await advanceTime(200);
    await animationFrame();
    expect("main[role='alert'] > p").toHaveText(
        "Among the 2 selected records, 1 are valid for this update.\nAre you sure you want to update 1 records?",
        { message: "A dialog box should appear when editing multiple timesheet names" }
    );
    await contains("footer > button[class='btn btn-secondary']").click();

    // Verify that bulk task editing is disabled when selected timesheets belong to different projects
    await contains("tbody > tr:first-child > td[name='task_id']").click();
    await contains("tbody > tr:first-child > td[name='task_id']").click();
    expect("tbody > tr:first-child > td[name='task_id'] > div > div > div").toHaveCount(0, {
        message: "Since task bulk‑editing is not allowed across different projects, no dropdown menu should appear",
    });

    // Verify that bulk project editing is disabled when selected timesheets belong to different projects
    await contains("tbody > tr:first-child > td[name='project_id']").click();
    await contains("tbody > tr:first-child > td[name='project_id']").click();
    expect("tbody > tr:first-child > td[name='project_id'] > div > div > div").toHaveCount(0, {
        message: "Since project bulk‑editing is disallowed, no dropdown menu should appear",
    });
});

test.tags("desktop");
test("hr.timesheet (list): when timesheet's with the same project are selected, task can be modified but project can't ", async () => {
    pyEnv["account.analytic.line"].create([
        {
            project_id: 1,
            task_id: 3,
            unit_amount: 1,
        },
        {
            project_id: 1,
            task_id: false,
            unit_amount: 2,
        },
    ]);
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
        arch: `
            <list multi_edit="1" js_class="timesheet_list_view">
                <field name="project_id"/>
                <field name="task_id"/>
                <field name="name"/>
            </list>
        `,
    });
    // Select the rows with the same project
    await contains(`.o_list_record_selector`).click();

    // Verify that bulk task editing is permitted when all selected timesheets share the same project
    await contains("tbody > tr:first-child > td[name='task_id']").click();
    await contains("tbody > tr:first-child > td[name='task_id']").click();
    expect("tbody > tr:first-child > td[name='task_id'] > div > div > div").toHaveCount(1, {
        message: "Since task bulk‑editing is allowed, a dropdown menu should appear.",
    });

    await contains("tbody > tr:first-child > td[name='task_id'] input").edit("Task 1 AdditionalInfo");
    await advanceTime(500);
    await animationFrame();
    expect("main[role='alert'] > p").toHaveText("Are you sure you want to update 2 records?", {
        message: "A dialog box should open when editing multiple timesheet tasks at once, if all the timesheet share a project"
    });
    await contains("footer > button[class='btn btn-secondary']").click();

    // Verify that bulk project editing is disabled when selected timesheets belong to the same project
    await contains("tbody > tr:first-child > td[name='project_id']").click();
    await contains("tbody > tr:first-child > td[name='project_id']").click();
    expect("tbody > tr:first-child > td[name='project_id'] > div > div > div").toHaveCount(0, {
        message: "Since project bulk‑editing is disallowed, no dropdown menu should appear",
    });
});

test.tags("desktop");
test("hr.timesheet (list): when only a single timesheet is selected, project can be modified  ", async () => {
    pyEnv["account.analytic.line"].create([
        {
            project_id: 1,
            task_id: 3,
            unit_amount: 1,
        },
    ]);
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
        arch: `
            <list multi_edit="1" js_class="timesheet_list_view">
                <field name="project_id"/>
                <field name="task_id"/>
                <field name="name"/>
            </list>
        `,
    });

    // Select the timesheet
    await contains(`.o_list_record_selector`).click();

    // Verify that single-timesheet project editing is allowed
    await contains("tbody > tr:first-child > td[name='project_id']").click();
    await contains("tbody > tr:first-child > td[name='project_id']").click();
    expect("tbody > tr:first-child > td[name='project_id'] > div > div > div").toHaveCount(1, {
        message: "Since project editing for a single timesheet is allowed, a dropdown menu should appear",
    });
    await contains("tbody > tr:first-child > td[name='project_id'] input").edit("Project 2");
    await advanceTime(500);
    await animationFrame();
    expect("tbody > tr:first-child > td[name='project_id']").toHaveText("Project 2", {
        message: "Updating the project should refresh the timesheet list",
    });
});
