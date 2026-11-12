import { beforeEach, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";
import {
    clickAllDaySlot,
    clickDate,
    selectAllDayRange,
    selectTimeRange,
} from "@web/../tests/views/calendar/calendar_test_helpers";

class HrEmployee extends models.ServerModel {
    _name = "hr.employee";
}

class HrAttendance extends models.Model {
    _name = "hr.attendance";

    check_in = fields.Datetime();
    check_out = fields.Datetime();
    employee_id = fields.Many2one({ relation: "hr.employee" });

    _views = {
        form: `<form><field name="check_in"/><field name="check_out"/><field name="employee_id"/></form>`,
    };
}

defineModels([HrEmployee, HrAttendance]);
defineMailModels();

const calendarArch = (mode) => `
    <calendar js_class="attendance_calendar_view" date_start="check_in" date_stop="check_out"
              mode="${mode}" quick_create="0" event_open_popup="1"/>`;

beforeEach(() => {
    mockDate("2019-03-13 08:00:00", +1);
    onRpc("res.users", "read", ({ args }) => [{ id: args[0][0], employee_id: [1, "Employee"] }]);
    onRpc("hr.attendance", "onchange", ({ kwargs }) => {
        expect.step(`isAllDay: ${kwargs.context.isAllDay}`);
        if (kwargs.context.isAllDay) {
            expect.step(`allDayDate: ${kwargs.context.allDayDate}`);
        }
    });
});

test("clicking a day in the all-day row sends isAllDay and the day", async () => {
    await mountView({ type: "calendar", resModel: "hr.attendance", arch: calendarArch("week") });
    await clickAllDaySlot("2019-03-13");
    expect.verifySteps(["isAllDay: true", "allDayDate: 2019-03-13"]);
});

test("clicking a day in the month view sends isAllDay and the day", async () => {
    await mountView({ type: "calendar", resModel: "hr.attendance", arch: calendarArch("month") });
    await clickDate("2019-03-13");
    expect.verifySteps(["isAllDay: true", "allDayDate: 2019-03-13"]);
});

test("selecting several days does not send isAllDay", async () => {
    await mountView({ type: "calendar", resModel: "hr.attendance", arch: calendarArch("week") });
    await selectAllDayRange("2019-03-13", "2019-03-15");
    expect.verifySteps(["isAllDay: undefined"]);
});

test("selecting a time slot does not send isAllDay", async () => {
    await mountView({ type: "calendar", resModel: "hr.attendance", arch: calendarArch("week") });
    await selectTimeRange("2019-03-13 10:00:00", "2019-03-13 12:00:00");
    expect.verifySteps(["isAllDay: undefined"]);
});
