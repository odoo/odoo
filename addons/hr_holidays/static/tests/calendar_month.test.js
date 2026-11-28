import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryOne, queryRect } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { mountView, onRpc } from "@web/../tests/web_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { HrLeave } from "@hr_holidays/../tests/mock_server/mock_models/hr_leave";

describe.current.tags("desktop");
defineHrHolidaysModels();

beforeEach(() => {
    mockDate("2024-01-03 12:00:00", 0);
    HrLeave._records = [
        {
            id: 1,
            employee_id: 100,
            state: "validate",
            date_from: "2024-01-09 08:00:00",
            date_to: "2024-01-09 12:00:00",
            work_entry_type_request_unit: "half_day",
            number_of_days: 0.5,
        },
        {
            id: 2,
            employee_id: 100,
            state: "validate",
            date_from: "2024-01-10 08:00:00",
            date_to: "2024-01-12 17:00:00",
            work_entry_type_request_unit: "day",
            number_of_days: 3,
        },
    ];
    onRpc("get_mandatory_days", () => ({}));
    onRpc("get_unusual_days", () => ({}));
    onRpc("get_special_days_data", () => ({ bankHolidays: [], mandatoryDays: [] }));
    onRpc("hr.employee", "get_time_off_dashboard_data", () => ({
        allocation_data: {},
        allocations_number: "",
    }));
});

function mountMonthCalendar(jsClass) {
    return mountView({
        type: "calendar",
        resModel: "hr.leave",
        arch: `
            <calendar js_class="${jsClass}"
                      date_start="date_from"
                      date_stop="date_to"
                      event_open_popup="1"
                      quick_create="0"
                      hide_time="1"
                      mode="month">
                <field name="display_name" string=""/>
                <field name="state" invisible="1"/>
            </calendar>`,
    });
}

const getShare = (eventId) =>
    queryOne(`.o_calendar_event[data-event-id='${eventId}']`).style.getPropertyValue("--o-working-day__share");

test("a time off of an employee is as high as its share of a working day", async () => {
    await mountMonthCalendar("time_off_calendar_dashboard");
    expect(".o_working_day_calendar").toHaveCount(1);
    expect(getShare(1)).toBe("0.5");
    // Several days are as high as the fullest one.
    expect(getShare(2)).toBe("1");
    expect(queryRect(".o_calendar_event[data-event-id='1']").height).toBeLessThan(
        queryRect(".o_calendar_event[data-event-id='2']").height
    );
});

test("an afternoon off ends its day, even with a blank morning", async () => {
    HrLeave._records.push({
        id: 3,
        employee_id: 100,
        state: "validate",
        date_from: "2024-01-16 13:00:00",
        date_to: "2024-01-16 17:00:00",
        work_entry_type_request_unit: "half_day",
        number_of_days: 0.5,
    });
    await mountMonthCalendar("time_off_calendar_dashboard");
    const getOffset = (eventId) =>
        queryOne(`.o_calendar_event[data-event-id='${eventId}']`).style.getPropertyValue("--o-working-day__offset");
    expect(getOffset(1)).toBe("0");
    expect(getOffset(3)).toBe("0.5");
});

test("the time off of several employees keeps a line each", async () => {
    HrLeave._records[1].employee_id = 200;
    await mountMonthCalendar("time_off_management_calendar");
    expect(".o_calendar_event").toHaveCount(2);
    expect(".o_working_day_calendar").toHaveCount(0);
});
