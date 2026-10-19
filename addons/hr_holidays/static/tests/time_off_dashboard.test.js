import { describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { defineModels, fields, getService, models, mountWebClient, onRpc } from "@web/../tests/web_test_helpers";
import { navigate } from "@web/../tests/views/calendar/calendar_test_helpers";
import { defineHrHolidaysModels } from "./hr_holidays_test_helpers";

describe.current.tags("desktop");

class HrLeave extends models.Model {
    _views = {
        calendar: `
            <calendar js_class="time_off_calendar_dashboard"
                      string="Time Off Request"
                      form_view_id="%(hr_holidays.hr_leave_view_form_dashboard_new_time_off)d"
                      event_open_popup="1"
                      date_start="date_from"
                      date_stop="date_to"
                      quick_create="0"
                      show_unusual_days="1"
                      color="color"
                      hide_time="1"
                      mode="year"
            >
                <field name="name"/>
                <field name="work_entry_type_id" filters="1" invisible="1" color="color"/>
                <field name="state" invisible="1"/>
            </calendar>
        `,
    };

    color = fields.Integer({ related: "work_entry_type_id.color" });
    date_from = fields.Datetime();
    date_to = fields.Datetime();
    department_id = fields.Many2one({ relation: "hr.department" });
    employee_id =  fields.Many2one({ relation: "hr.employee" });
    work_entry_type_id = fields.Many2one({ relation: "hr.work.entry.type" });
    holiday_type = fields.Char();
    name = fields.Char();
    number_of_days = fields.Integer();
    state = fields.Char();
}

class HrWorkEntryType extends models.Model {
    name = fields.Char();
    color = fields.Integer();
}

defineHrHolidaysModels();
defineModels([HrLeave, HrWorkEntryType]);

onRpc("hr.employee", "get_time_off_dashboard_data", () => (
    {has_accrual_allocation: true, allocation_data: {}, allocations_number: ""}
));
onRpc("hr.employee", "get_mandatory_days", () => ({}));
onRpc("hr.employee", "get_special_days_data", () => ({ mandatoryDays: [], bankHolidays: [] }));
onRpc("hr.leave", "get_unusual_days", () => ({}));
onRpc("hr.leave", "has_access", () => true);
onRpc("hr.work.entry.type", "has_accrual_allocation", () => true);

test(`test employee is passed to get_time_off_dashboard_data`, async () => {
    onRpc("hr.employee", "get_time_off_dashboard_data", ({ kwargs }) => {
        expect.step(kwargs.context.employee_id);
    });

    await mountWebClient();
    await getService("action").doAction({
        id: 1,
        res_model: "hr.leave",
        type: "ir.actions.act_window",
        views: [[false, "calendar"]],
        context: { employee_id: [200] },
        domain: [["employee_id", "in", [200]]],
    });
    expect.verifySteps([200]);
});

test(`test basic rendering`, async () => {
    mockDate("2025-03-18 08:00:00");
    onRpc("hr.employee", "get_mandatory_days", () => ({ "2025-03-17": 5 }));
    onRpc("hr.employee", "get_special_days_data", () => ({
        mandatoryDays: [
            {
                id: -2,
                colorIndex: 5,
                end: "2025-03-17T23:59:59.999999",
                endType: "datetime",
                isAllDay: true,
                start: "2025-03-17T00:00:00",
                startType: "datetime",
                title: "Test Mandatory Day",
            },
        ],
        bankHolidays: [],
    }));

    await mountWebClient();
    await getService("action").doAction({
        id: 1,
        res_model: "hr.leave",
        type: "ir.actions.act_window",
        views: [[false, "calendar"]],
        context: { employee_id: [200] },
        domain: [["employee_id", "in", [200]]],
    });
    expect(`.o_calendar_filter:contains("Legend")`).toHaveCount(1);
    expect(`.o_calendar_filter:contains("To Approve")`).toHaveCount(1);
    expect(`.o_calendar_filter:contains("Mar 17, 2025 : Test Mandatory Day")`).toHaveCount(1);
    expect(`.o_calendar_day.hr_mandatory_day_5[data-date="2025-03-17"]`).toHaveCount(1);
});

test(`Company Holidays should be limited to the current month and upcoming`, async () => {
    mockDate("2024-01-15 08:00:00");
    onRpc("hr.employee", "get_special_days_data", () => ({
        mandatoryDays: [],
        bankHolidays: [
            {
                id: -1,
                colorIndex: 0,
                end: "2023-12-25T23:59:59.999999",
                endType: "datetime",
                isAllDay: true,
                start: "2023-12-25T00:00:00",
                startType: "datetime",
                title: "Last month holiday",
            },
            {
                id: -2,
                colorIndex: 0,
                end: "2024-01-05T23:59:59.999999",
                endType: "datetime",
                isAllDay: true,
                start: "2024-01-05T00:00:00",
                startType: "datetime",
                title: "Earlier this month holiday",
            },
            {
                id: -3,
                colorIndex: 0,
                end: "2024-02-10T23:59:59.999999",
                endType: "datetime",
                isAllDay: true,
                start: "2024-02-10T00:00:00",
                startType: "datetime",
                title: "Next month holiday",
            },
        ],
    }));

    await mountWebClient();
    await getService("action").doAction({
        id: 1,
        res_model: "hr.leave",
        type: "ir.actions.act_window",
        views: [[false, "calendar"]],
        context: { employee_id: [200] },
        domain: [["employee_id", "in", [200]]],
    });

    // a holiday from a past month is dropped entirely
    expect(`.o_calendar_filter:contains("Last month holiday")`).toHaveCount(0);
    // a past holiday within the current month is kept but muted
    expect(`.o_calendar_filter li.text-muted:contains("Jan 5, 2024 : Earlier this month holiday")`).toHaveCount(1);
    // an upcoming holiday is kept and highlighted
    expect(`.o_calendar_filter li.fw-bold:contains("Feb 10, 2024 : Next month holiday")`).toHaveCount(1);
});

test("browsing to a past period still hides holidays from before the real current month", async () => {
    mockDate("2024-01-15 08:00:00");
    const holidayDate = "2023-12-20";
    // mirrors the real server, which legitimately returns holidays inside whatever
    // range the calendar currently displays, including a past one
    onRpc("hr.employee", "get_special_days_data", ({ args }) => {
        const [dateStart, dateEnd] = args;
        const inRange = dateStart.slice(0, 10) <= holidayDate && holidayDate <= dateEnd.slice(0, 10);
        return {
            mandatoryDays: [],
            bankHolidays: inRange
                ? [
                      {
                          id: -1,
                          colorIndex: 0,
                          end: `${holidayDate}T23:59:59.999999`,
                          endType: "datetime",
                          isAllDay: true,
                          start: `${holidayDate}T00:00:00`,
                          startType: "datetime",
                          title: "Past year holiday",
                      },
                  ]
                : [],
        };
    });

    await mountWebClient();
    await getService("action").doAction({
        id: 1,
        res_model: "hr.leave",
        type: "ir.actions.act_window",
        views: [[false, "calendar"]],
        context: { employee_id: [200] },
        domain: [["employee_id", "in", [200]]],
    });
    expect(`.o_calendar_filter:contains("Company Holidays")`).toHaveCount(0);

    // the holiday section is anchored on the real current date, not on the period
    // the calendar happens to display: browsing to the year the holiday falls in
    // doesn't surface it, since it's still before the real current month
    await navigate("prev");
    expect(`.o_calendar_filter:contains("Company Holidays")`).toHaveCount(0);
});
