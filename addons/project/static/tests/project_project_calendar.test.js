import { expect, test, beforeEach, describe } from "@odoo/hoot";
import { mockDate, runAllTimers } from "@odoo/hoot-mock";
import { click, queryAllTexts } from "@odoo/hoot-dom";

import { mountView, onRpc } from "@web/../tests/web_test_helpers";

import { defineProjectModels, ProjectProject } from "./project_models";

describe.current.tags("desktop");
defineProjectModels();

beforeEach(() => {
    mockDate("2024-01-03 12:00:00", +0);

    ProjectProject._records = [
        {
            id: 1,
            name: "Project-1",
            date: "2024-01-09 07:00:00",
            date_start: "2024-01-03 12:00:00",
            display_name: "Task-1",
        },
    ];

    onRpc("has_access", () => true);
});

const calendarMountParams = {
    resModel: "project.project",
    type: "calendar",
    arch: `
        <calendar date_start="date_start" mode="week" js_class="project_project_calendar">
            <field name="name"/>
        </calendar>
    `,
};

test("check 'Edit Project' and 'View Tasks' buttons is in Project Calendar Popover", async () => {
    onRpc("get_formview_id", ({ args, model }) => {
        console.log("qqqq", args);
        expect(model).toBe("project.project");
        expect(args[0]).toEqual([1]);
        return false;
    });
    onRpc("/web/action/load", () => {
        return Promise.resolve({
            type: "ir.actions.act_window",
            res_model: "project.task",
            views: [[false, "kanban"]],
        });
    });

    await mountView(calendarMountParams);

    expect(".fc-event-main").toHaveCount(1);
    await click(".fc-event-main");
    await runAllTimers();
    expect(".o_popover").toHaveCount(1);
    expect(".o_popover .card-footer .btn").toHaveCount(3);
    expect(queryAllTexts(".o_popover .card-footer .btn")).toEqual([
        "View Tasks",
        "Edit Project",
        "Delete",
    ]);

    await click(".o_popover .card-footer a:contains(View Tasks)");
    await click(".o_popover .card-footer a:contains(Edit Project)");
});
