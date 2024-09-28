import { expect, test, beforeEach, describe } from "@odoo/hoot";
import { mockDate, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { click, queryOne } from "@odoo/hoot-dom";

import { mountView, onRpc } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectTask } from "./project_models";

describe.current.tags("desktop");
defineProjectModels();

beforeEach(() => {
    mockDate("2024-01-03 12:00:00", +0);

    ProjectTask._views["form,false"] = `
        <form>
            <field name="id"/>
            <field name="name"/>
            <field name="date_deadline"/>
            <field name="planned_date_begin"/>
        </form>
    `;

    ProjectTask._records = [
        {
            id: 1,
            name: "Task-1",
            date_deadline: "2024-01-09 07:00:00",
            create_date: "2024-01-03 12:00:00",
            project_id: 1,
            stage_id: 1,
            state: "01_in_progress",
            user_ids: [],
            display_name: "Task-1",
        },
    ];

    onRpc("has_access", () => true);
});

const calendarMountParams = {
    resModel: "project.task",
    type: "calendar",
    arch: `
        <calendar date_start="date_deadline" mode="month"
                    js_class="project_task_calendar">
            <field name="project_id" widget="project" invisible="context.get('default_project_id', False)"/>
            <field name="stage_id" invisible="not project_id or not stage_id" widget="task_stage_with_state_selection"/>
        </calendar>
    `,
};

test("test Project Task Calendar Popover with task_stage_with_state_selection widget", async () => {
    await mountView(calendarMountParams);

    await click("a.fc-daygrid-event");

    // Skipping setTimeout while clicking event in calendar for calendar popover to appear.
    // There is a timeout set in the useCalendarPopover.
    await runAllTimers();

    expect(queryOne(".o_field_task_stage_with_state_selection div").childElementCount).toBe(2);
});

test("test task_stage_with_state_selection widget with non-editable state", async () => {
    await mountView({
        ...calendarMountParams,
        arch: `
            <calendar date_start="date_deadline" mode="month"
                        js_class="project_task_calendar">
                <field name="project_id" widget="project" invisible="context.get('default_project_id', False)"/>
                <field name="stage_id" invisible="not project_id or not stage_id" widget="task_stage_with_state_selection" options="{'state_readonly': True}"/>
            </calendar>
        `,
    });

    await click("a.fc-daygrid-event");

    // Skipping setTimeout while clicking event in calendar for calendar popover to appear.
    // There is a timeout set in the useCalendarPopover.
    await runAllTimers();

    await click("button[title='In Progress']");

    expect(".project_task_state_selection_menu").toHaveCount(0);
});

test("test task_stage_with_state_selection widget with editable state", async () => {
    await mountView({
        ...calendarMountParams,
        arch: `
            <calendar date_start="date_deadline" mode="month"
                        js_class="project_task_calendar">
                <field name="project_id" widget="project" invisible="context.get('default_project_id', False)"/>
                <field name="stage_id" invisible="not project_id or not stage_id" widget="task_stage_with_state_selection" options="{'state_readonly': False}"/>
            </calendar>
        `,
    });

    await click("a.fc-daygrid-event");

    // Skipping setTimeout while clicking event in calendar for calendar popover to appear.
    // There is a timeout set in the useCalendarPopover.
    await runAllTimers();

    await click(".o-dropdown div[title='In Progress']");
    await animationFrame();
    expect(".project_task_state_selection_menu").toHaveCount(1);

    await click(".o_status_green"); // Checking if click on the state in selection menu works(changes in record)
    await animationFrame();
    expect(".o-dropdown .o_status").toHaveStyle({ color: "rgb(0, 136, 24)" });
});
