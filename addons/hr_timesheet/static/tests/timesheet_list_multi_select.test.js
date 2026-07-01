import { test, expect } from "@odoo/hoot";
import { advanceTime, tick } from "@odoo/hoot-mock";
import { mountView, contains } from "@web/../tests/web_test_helpers";
import { defineTimesheetModels } from "./hr_timesheet_models";

defineTimesheetModels();
test("hr.timesheet (list): multi-edit", async () => {
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
        arch: `
            <list editable="top" string="Timesheet Activities" sample="1" multi_edit="1" js_class="timesheet_list_view">
                <field name="project_id" on_change="1" can_create="True" can_write="True"/>
                <field name="task_id" options="{'no_create_edit': True, 'no_open': True}" on_change="1" can_create="True" can_write="True"/>
                <field name="name"/>
            </list>
        `,
    });
    // Select all rows
    await contains("input[id='checkbox-comp-1']").click();

    // Verify that bulk editing of timesheet names is permitted
    await contains("tr[data-id='datapoint_4'] > td[name='name']").click();
    await contains("tr[data-id='datapoint_4'] > td[name='name'] > div > input").edit("Sample Text");
    await advanceTime(500);
    await tick();
    expect("main[role='alert'] > p").toHaveText(
        "Among the 3 selected records, 2 are valid for this update.\nAre you sure you want to update 2 records?",
        { message: "A dialog box should appear when editing multiple timesheet names" }
    );
    await contains("footer > button[class='btn btn-secondary']").click();

    // Verify that bulk task editing is disabled when selected timesheets belong to different projects
    await contains("tr[data-id='datapoint_5'] > td[name='task_id']").click();
    await contains("tr[data-id='datapoint_5'] > td[name='task_id']").click();
    expect("tr[data-id='datapoint_5'] > td[name='task_id'] > div > div > div").toHaveCount(0, {
        message: "Since task bulk‑editing is not allowed across different projects, no dropdown menu should appear",
    });

    // Verify that bulk project editing is disabled when selected timesheets belong to different projects
    await contains("tr[data-id='datapoint_5'] > td[name='project_id']").click();
    await contains("tr[data-id='datapoint_5'] > td[name='project_id']").click();
    expect("tr[data-id='datapoint_5'] > td[name='project_id'] > div > div > div").toHaveCount(0, {
        message: "Since project bulk‑editing is disallowed, no dropdown menu should appear",
    });

    // Select two rows with the same project
    await contains("input[id='checkbox-comp-1']").click();
    await contains("input[id='checkbox-comp-1']").click();
    await contains("input[id='checkbox-comp-2']").click();
    await contains("input[id='checkbox-comp-3']").click();

    // Verify that bulk task editing is permitted when all selected timesheets share the same project
    await contains("tr[data-id='datapoint_5'] > td[name='task_id']").click();
    await contains("tr[data-id='datapoint_5'] > td[name='task_id']").click();
    expect("tr[data-id='datapoint_5'] > td[name='task_id'] > div > div > div").toHaveCount(1, {
        message: "Since task bulk‑editing is allowed, a dropdown menu should appear.",
    });
    await contains("tr[data-id='datapoint_5'] > td[name='task_id'] > div > div > div > div > div > input").edit("Task 1 AdditionalInfo");
    await advanceTime(500);
    await tick();
    expect("main[role='alert'] > p").toHaveText("Are you sure you want to update 2 records?", {
        message: "A dialog box should open when editing multiple timesheet tasks at once, if all the timesheet share a project"
    });
    await contains("footer > button[class='btn btn-secondary']").click();

    // Verify that bulk project editing is disabled when selected timesheets belong to the same project
    await contains("tr[data-id='datapoint_5'] > td[name='project_id']").click();
    await contains("tr[data-id='datapoint_5'] > td[name='project_id']").click();
    expect("tr[data-id='datapoint_5'] > td[name='project_id'] > div > div > div").toHaveCount(0, {
        message: "Since project bulk‑editing is disallowed, no dropdown menu should appear",
    });

    // Select a single timesheet
    await contains("input[id='checkbox-comp-1']").click();
    await contains("input[id='checkbox-comp-3']").click();

    // Verify that single-timesheet project editing is allowed
    await contains("tr[data-id='datapoint_4'] > td[name='project_id']").click();
    await contains("tr[data-id='datapoint_4'] > td[name='project_id']").click();
    expect("tr[data-id='datapoint_4'] > td[name='project_id'] > div > div > div").toHaveCount(1, {
        message: "Since project editing for a single timesheet is allowed, a dropdown menu should appear",
    });
    await contains("tr[data-id='datapoint_4'] > td[name='project_id'] > div > div > div > div > div > input").edit("Project 2");
    await advanceTime(500);
    await tick();
    expect("tr[data-id='datapoint_4'] > td[name='project_id']").toHaveText("Project 2", {
        message: "Updating the project should refresh the timesheet list",
    });
});
