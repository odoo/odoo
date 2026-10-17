import { expect, test } from "@odoo/hoot";
import { queryAll, waitFor } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class HrEmployee extends models.ServerModel {
    _name = "hr.employee";
    _records = [{ id: 1, name: "Test Employee" }];
}

class HrAttendance extends models.ServerModel {
    _name = "hr.attendance";
    employee_id = fields.Many2one({ relation: "hr.employee" });
    check_in = fields.Datetime();
    check_out = fields.Datetime();
    _records = [];
}

defineModels({ HrEmployee, HrAttendance });
defineMailModels();

function getShadedHeight(date) {
    return queryAll(
        `[role='gridcell'][data-date='${date}'] .o_calendar_non_business`
    ).reduce((sum, el) => sum + el.getBoundingClientRect().height, 0);
}

test("non-working hours are shaded outside the employee schedule", async () => {
    // Monday 12 Oct 2026
    mockDate("2026-10-12 10:00:00");

    onRpc("hr.attendance", "get_working_hours_for_calendar", () => [
        // FullCalendar: Sunday = 0, so Monday = 1
        { daysOfWeek: [1], startTime: "09:00", endTime: "17:00" },
    ]);
    // the overview sidebar loads its own data
    onRpc("get_attendance_data_by_employee", () => ({}));

    await mountView({
        type: "calendar",
        resModel: "hr.attendance",
        arch: `
            <calendar js_class="attendance_calendar_view" date_start="check_in" date_stop="check_out" mode="week">
                <field name="employee_id"/>
            </calendar>`,
        context: { employee_id: 1 },
    });
    await waitFor("[role='gridcell'][data-date='2026-10-12']");
    await animationFrame();

    const monday = getShadedHeight("2026-10-12");
    const tuesday = getShadedHeight("2026-10-13");

    // Monday has a 09:00-17:00 working window, so part of it is shaded
    expect(monday).toBeGreaterThan(0);
    // Tuesday has no working hours, so more of it is shaded than Monday
    expect(tuesday).toBeGreaterThan(monday);
});
