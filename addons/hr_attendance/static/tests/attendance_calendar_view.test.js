import { expect, test } from "@odoo/hoot";
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
    _records = [];
    _views = {
        list: `<list><field name="employee_id"/><field name="check_in"/></list>`,
        form: `<form><field name="employee_id"/></form>`,
        calendar: `<calendar js_class="attendance_calendar_view"
                date_start="check_in" date_stop="check_out" mode="week" show_unusual_days="True">
        </calendar>`,
        search: `<search>
            <filter name="groupby_week" string="Check In" context="{'group_by': 'check_in:week'}"/>
        </search>`,
    };
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

test.tags("desktop");
test("smart button on the employee profile opens a calendar with that employee's working hours", async () => {
    mockDate("2026-10-12 10:00:00");
    mockTimeZone("Asia/Kolkata");
    const requestedEmployees = [];

    // mirrors the action returned by the real smart button method
    onRpc("hr.employee", "action_open_last_month_attendances", () => ({
        type: "ir.actions.act_window",
        name: "Attendances This Month",
        res_model: "hr.attendance",
        views: [[false, "list"], [false, "form"], [false, "calendar"]],
        domain: [["employee_id", "=", 4]],
        context: { search_default_groupby_week: 1 },
    }));
    onRpc("hr.attendance", "get_working_hours_for_calendar", ({ args, kwargs }) => {
        expect(kwargs.context.tz).toBe("Asia/Kolkata");
        requestedEmployees.push(args[0]);
        return [{ daysOfWeek: [1], startTime: "09:00", endTime: "17:00" }];
    });
    onRpc("hr.attendance", "get_unusual_days", ({ kwargs }) => {
        expect(kwargs.context.employee_id).toBe(4);
        expect.step("unusual days requested");
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

    // 1. smart button opens the list, grouped by week
    await contains(".oe_stat_button").click();
    expect(".o_list_view").toHaveCount(1);
    expect(".o_searchview_facet").toHaveCount(1);
    expect(".o_searchview_facet").toHaveText("Check In: Week");
    await contains(".o_facet_remove").click();
    expect(".o_searchview_facet").toHaveCount(0);

    // 2. switch to the calendar
    await contains(".o_switch_view.o_calendar").click();
    await waitFor("[role='gridcell'][data-date='2026-10-12']");
    await animationFrame();

    // 3. the working hours requested are those of the profile's employee
    expect(requestedEmployees).toEqual([4]);
    expect.verifySteps(["unusual days requested"]);

    // 4. and they are shaded: Monday partly, Tuesday (no hours) more
    const monday = getShadedHeight("2026-10-12");
    const tuesday = getShadedHeight("2026-10-13");
    expect(monday).toBeGreaterThan(0);
    expect(tuesday).toBeGreaterThan(monday);
});
