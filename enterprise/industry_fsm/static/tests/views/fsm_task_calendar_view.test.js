import { describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";

import { clickDate } from "@web/../tests/views/calendar/calendar_test_helpers";
import { mountView, onRpc } from "@web/../tests/web_test_helpers";

import { defineProjectModels } from "@project/../tests/project_models";
import { ProjectTask } from "@project_enterprise/../tests/task_gant_model";

describe.current.tags("desktop");
ProjectTask._views.form = `
    <form>
        <field name="id"/>
        <field name="name"/>
        <field name="date_deadline"/>
        <field name="planned_date_begin"/>
    </form>
`;
defineProjectModels();
onRpc("has_access", () => true);

test("Fsm task calendar view", async () => {
    mockDate("2024-01-03 12:00:00", 0);
    await mountView({
        resModel: "project.task",
        type: "calendar",
        arch: /* xml */ `
            <calendar
                date_start="planned_date_start"
                date_stop="date_deadline"
                event_open_popup="1"
                mode="month"
                js_class="fsm_task_calendar"
                quick_create="0"
            />
        `,
    });

    expect(".o_calendar_view").toHaveCount(1);

    await clickDate("2024-01-09");

    expect("div[name='planned_date_begin'] input").toHaveValue("01/09/2024 00:00:00", {
        message:
            "The planned_date_begin field should hold the planned_date_start value in the record thanks to the fsmCalendarModel makeContextDefault inheritance",
    });
});
