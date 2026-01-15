import { describe, expect, test } from "@odoo/hoot";
import { click, edit } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountView } from "@web/../tests/web_test_helpers";

import { HRTimesheet, defineTimesheetModels } from "./hr_timesheet_models";

HRTimesheet._views.list = `
    <list editable="bottom">
        <field name="project_id"/>
        <field name="task_id" widget="task_with_hours" context="{ 'default_project_id': project_id }"/>
        <field name="unit_amount"/>
    </list>
`;
defineTimesheetModels();
describe.current.tags("desktop");

async function _expectCreateAndEdit(rowN) {
    const taskField = `.o_list_table .o_data_row:nth-of-type(${rowN}) .o_list_many2one[name=task_id]`;
    await click(taskField);
    await animationFrame();
    await edit("NonExistingTask", { confirm: false });
    await click(`${taskField} input`);
    await animationFrame();
    return expect(
        '.o_list_many2one[name=task_id] .dropdown ul li:contains(Create "NonExistingTask")'
    );
}

test("hr.timesheet (tree): quick create is enabled when project_id is set", async () => {
    await mountView({
        resModel: "account.analytic.line",
        type: "list",
    });
    (await _expectCreateAndEdit(2)).toBeVisible();
});

test("hr.timesheet (tree): quick create is no enabled when project_id is not set", async () => {
    await mountView({
        resModel: "account.analytic.line",
        type: "list",
    });
    (await _expectCreateAndEdit(3)).not.toHaveCount();
});

test("hr.timesheet (tree): the text of the task includes hours in the drop down but not in the line", async () => {
    await mountView({
        resModel: "account.analytic.line",
        type: "list",
    });
    const taskField = ".o_list_table .o_data_row:first-of-type .o_list_many2one[name=task_id]";
    expect(taskField).toHaveText("Task 3");
    await click(taskField);
    await animationFrame();
    await click(`${taskField} input`);
    await animationFrame();
    expect(`${taskField} .dropdown ul li:contains("AdditionalInfo")`).toHaveCount(3);
});

test("project.task (tree): progress bar color", async () => {
    await mountView({
        resModel: "project.task",
        type: "list",
        arch: `
            <list>
                <field name="name"/>
                <field name="project_id"/>
                <field name="progress" widget="project_task_progressbar" options="{'overflow_class': 'bg-danger'}"/>
            </list>
        `,
    });

    expect("div.o_progressbar .bg-success").toHaveCount(1, {
        message: "Task 1 having progress = 50 < 80 => green color",
    });
    expect("div.o_progressbar .bg-warning").toHaveCount(1, {
        message: "Task 2 having progress = 80 >= 80 => orange color",
    });
    expect("div.o_progressbar .bg-success").toHaveCount(1, {
        message: "Task 3 having progress = 101 > 100 => red color",
    });
});
