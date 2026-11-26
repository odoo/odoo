import { beforeEach, expect, test } from "@odoo/hoot";
import { queryAll, waitFor } from "@odoo/hoot-dom";
import { animationFrame, mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    contains,
    defineModels,
    fields,
    getService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import {
    clickAllDaySlot,
    clickDate,
    clickEvent,
    findEvent,
    selectAllDayRange,
    selectTimeRange,
} from "@web/../tests/views/calendar/calendar_test_helpers";
import { WebClient } from "@web/webclient/webclient";

class HrEmployee extends models.ServerModel {
    _name = "hr.employee";
    display_attendances = fields.Boolean();
    hours_last_month_display = fields.Char({ readonly: true });
    _records = [
        { id: 1, name: "Test Employee" },
        {
            id: 4,
            name: "Target Employee",
            display_attendances: true,
            hours_last_month_display: "8:00",
        },
    ];
    _views = {
        form: `<form>
            <sheet>
                <div class="oe_button_box" name="button_box">
                    <field name="display_attendances" invisible="1"/>
                    <button name="action_open_last_month_attendances"
                            class="oe_stat_button"
                            icon="schedule"
                            type="object"
                            invisible="not display_attendances"
                            help="Worked hours this month">
                        <div class="o_field_widget o_stat_info">
                            <span class="o_stat_value">
                                <field name="hours_last_month_display" readonly="1"/>
                            </span>
                        </div>
                    </button>
                </div>
            </sheet>
        </form>`,
        search: `<search/>`,
    };
}

class HrAttendance extends models.ServerModel {
    _name = "hr.attendance";
    employee_id = fields.Many2one({ relation: "hr.employee" });
    check_in = fields.Datetime();
    check_out = fields.Datetime();
    _records = [
        {
            id: 1,
            employee_id: 4,
            check_in: "2026-10-12 03:30:00",
            check_out: "2026-10-12 11:30:00",
        },
    ];
    _views = {
        list: `<list><field name="employee_id"/><field name="check_in"/></list>`,
        form: `<form>
            <field name="check_in"/>
            <field name="check_out"/>
            <field name="employee_id"/>
            <footer>
                <button string="Save" special="save" class="btn btn-primary" close="1"/>
                <button special="cancel" class="btn-secondary" close="1"/>
                <button string="Delete" name="unlink" type="object" class="btn btn-danger ms-auto"
                    close="1" confirm="Are you sure you want to delete this attendance?"/>
            </footer>
        </form>`,
        calendar: `<calendar js_class="attendance_calendar_view"
                date_start="check_in" date_stop="check_out" mode="week" show_unusual_days="True">
        </calendar>`,
        search: `<search/>`,
    };
}

defineModels({ HrEmployee, HrAttendance });
defineMailModels();

const calendarArch = (mode) => `
    <calendar js_class="attendance_calendar_view" date_start="check_in" date_stop="check_out"
              mode="${mode}" quick_create="0" event_open_popup="1"/>`;

beforeEach(() => {
    mockDate("2019-03-13 08:00:00", +1);
    onRpc("hr.attendance", "get_attendance_dashboard_data", () => ({}));
    onRpc("res.users", "read", ({ args }) => [{ id: args[0][0], employee_id: [1, "Employee"] }]);
    // the working hours of the schedule, shaded by the calendar (see the tests below)
    onRpc("hr.attendance", "get_working_hours_for_calendar", () => []);
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

test.tags("desktop");
test("smart button on the employee profile opens a calendar with that employee's working hours", async () => {
    mockDate("2026-10-12 10:00:00");
    mockTimeZone("Asia/Kolkata");
    const requestedEmployees = [];
    const unusualDaysEmployees = [];
    const workingHoursTimezones = [];

    // mirrors the action returned by the real smart button method
    onRpc("hr.employee", "action_open_last_month_attendances", () => ({
        type: "ir.actions.act_window",
        name: "Attendances This Month",
        res_model: "hr.attendance",
        views: [
            [false, "list"],
            [false, "form"],
            [false, "calendar"],
        ],
        domain: [["employee_id", "=", 4]],
    }));
    onRpc("hr.attendance", "get_working_hours_for_calendar", ({ args, kwargs }) => {
        requestedEmployees.push(args[0]);
        workingHoursTimezones.push(kwargs.context.tz);
        return [{ daysOfWeek: [1], startTime: "09:00", endTime: "17:00" }];
    });
    onRpc("hr.attendance", "get_unusual_days", ({ kwargs }) => {
        unusualDaysEmployees.push(kwargs.context.employee_id);
        return {};
    });
    onRpc("get_attendance_data_by_employee", () => ({}));

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        type: "ir.actions.act_window",
        res_model: "hr.employee",
        res_id: 4,
        views: [[false, "form"]],
    });

    // 1. the smart button opens the list, not grouped
    await contains(".oe_stat_button").click();
    expect(".o_list_view").toHaveCount(1);
    expect(".o_group_header").toHaveCount(0);

    // 2. switch to the calendar
    await contains(".o_switch_view.o_calendar").click();
    await waitFor("[role='gridcell'][data-date='2026-10-12']");
    await animationFrame();

    // 3. both requests target the profile's employee, in the grid timezone
    expect(requestedEmployees).toEqual([4]);
    expect(workingHoursTimezones).toEqual(["Asia/Kolkata"]);
    expect(unusualDaysEmployees.length).toBeGreaterThan(0);
    for (const employeeId of unusualDaysEmployees) {
        expect(employeeId).toBe(4);
    }

    // 4. and the hours are shaded: Monday partly, Tuesday (no hours) more
    const monday = getShadedHeight("2026-10-12");
    const tuesday = getShadedHeight("2026-10-13");
    expect(monday).toBeGreaterThan(0);
    expect(tuesday).toBeGreaterThan(monday);
});

test("clicking an attendance opens its form dialog instead of the popover", async () => {
    // Monday 12 Oct 2026, the day of the attendance
    mockDate("2026-10-12 10:00:00");
    await mountView({ type: "calendar", resModel: "hr.attendance", arch: calendarArch("week") });

    await clickEvent(1);
    await waitFor(".o_dialog .o_form_view");
    expect(".o_cw_popover").toHaveCount(0);
});

test("deleting an attendance from its form dialog removes it from the calendar", async () => {
    mockDate("2026-10-12 10:00:00");
    onRpc("hr.attendance", "unlink", () => {
        expect.step("unlink");
    });
    await mountView({ type: "calendar", resModel: "hr.attendance", arch: calendarArch("week") });
    expect(findEvent(1)).not.toBe(null);

    await clickEvent(1);
    await contains(".o_dialog footer .btn-danger").click();
    await contains(".o_dialog .modal-footer .btn-primary:contains(Ok)").click();
    expect.verifySteps(["unlink"]);
    expect(".o_dialog").toHaveCount(0);
    expect(findEvent(1)).toBe(null);
});
