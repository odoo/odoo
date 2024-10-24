import { expect, test, beforeEach, describe } from "@odoo/hoot";
import { click, edit } from "@odoo/hoot-dom";
import { contains, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { mockDate, animationFrame } from "@odoo/hoot-mock";

import { defineTodoModels } from "./todo_test_helpers";
import { ProjectTask } from "./mock_server/mock_models/project_task";

describe.current.tags("desktop");
defineTodoModels();

beforeEach(() => {
    mockDate("2022-01-03 12:00:00", +0);

    ProjectTask._views["form,false"] = `
        <form>
            <field name="name"/>
            <field name="date_deadline"/>
        </form>
    `;

    onRpc("has_access", () => true);
});

const calendarMountParams = {
    resModel: "project.task",
    type: "calendar",
    arch: `
        <calendar date_start="date_deadline" mode="month"
                    js_class="project_task_calendar">
            <field name="name"/>
            <field name="priority" widget="priority"/>
            <field name="tag_ids"/>
        </calendar>
    `,
};

test("test creation of todo from the calendar view", async () => {
    await mountView(calendarMountParams);

    expect(".fc-daygrid-event").toHaveCount(2, {
        message: "The calendar view should have 2 todos",
    });

    // click on today's cell to create a new todo
    await contains(".fc-day-today").click();
    await animationFrame();

    expect(".o-calendar-quick-create").toBeVisible();
    click("[name=title]");
    edit("go running");
    await contains(`.o-calendar-quick-create--create-btn`).click();
    await animationFrame();

    expect(".fc-daygrid-event").toHaveCount(3, {
        message: "The calendar view should now have 3 todos",
    });
});
