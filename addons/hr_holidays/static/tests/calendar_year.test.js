import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts, waitFor } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { mountView, onRpc } from "@web/../tests/web_test_helpers";
import { clickDate } from "@web/../tests/views/calendar/calendar_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { HrLeave } from "@hr_holidays/../tests/mock_server/mock_models/hr_leave";

describe.current.tags("desktop");
defineHrHolidaysModels();

async function mountYearCalendar() {
    onRpc("get_mandatory_days", () => ({}));
    onRpc("get_unusual_days", () => ({}));
    onRpc("get_special_days_data", () => ({ bankHolidays: [], mandatoryDays: [] }));
    onRpc("hr.employee", "get_time_off_dashboard_data", () => ({
        has_accrual_allocation: true,
        allocation_data: {},
        allocations_number: "",
    }));
    await mountView({
        type: "calendar",
        resModel: "hr.leave",
        arch: `
            <calendar js_class="time_off_calendar_dashboard"
                      date_start="date_from"
                      date_stop="date_to"
                      event_open_popup="1"
                      quick_create="0"
                      create="0"
                      hide_time="1"
                      mode="year">
                <field name="display_name" string=""/>
                <field name="work_entry_type_id" filters="1" invisible="1" color="color"/>
                <field name="state" invisible="1"/>
            </calendar>`,
    });
}

test("a time off in days ends on the day its exclusive bound closes", async () => {
    mockDate("2024-01-03 12:00:00", 0);
    HrLeave._records = [
        {
            id: 1,
            employee_id: 100,
            state: "validate",
            date_from: "2024-01-09 00:00:00",
            date_to: "2024-01-11 00:00:00",
            work_entry_type_request_unit: "day",
        },
    ];
    await mountYearCalendar();

    // Midnight on the 11th closes the 10th: the request covers the 9th and the 10th.
    await clickDate("2024-01-09");
    await waitFor(".o_cw_popover_holidays");
    expect(queryAllTexts(".o_cw_popover_holidays .fw-bold")).toEqual(["January 9-10, 2024"]);

    await clickDate("2024-01-10");
    await waitFor(".o_cw_popover_holidays");
    expect(".o_cw_popover_holidays .o_cw_popover_link").toHaveCount(1);

    await clickDate("2024-01-11");
    expect(".o_cw_popover_holidays").toHaveCount(0);
});

test("time off covering the same days shares a group", async () => {
    mockDate("2024-01-03 12:00:00", 0);
    HrLeave._records = [
        {
            id: 1,
            employee_id: 100,
            state: "validate",
            date_from: "2024-01-09 00:00:00",
            date_to: "2024-01-10 00:00:00",
            work_entry_type_request_unit: "day",
        },
        {
            id: 2,
            employee_id: 200,
            state: "validate",
            date_from: "2024-01-09 08:00:00",
            date_to: "2024-01-09 12:00:00",
            work_entry_type_request_unit: "hour",
        },
    ];
    await mountYearCalendar();

    // The day request stops at midnight on the 10th, so both requests name the 9th alone.
    await clickDate("2024-01-09");
    await waitFor(".o_cw_popover_holidays");
    expect(queryAllTexts(".o_cw_popover_holidays .fw-bold")).toEqual(["January 9, 2024"]);
    expect(".o_cw_popover_holidays .o_cw_popover_link").toHaveCount(2);
});

test("a time off in hours ends inside the day it names", async () => {
    mockDate("2024-01-03 12:00:00", 0);
    HrLeave._records = [
        {
            id: 1,
            employee_id: 100,
            state: "validate",
            date_from: "2024-01-09 08:00:00",
            date_to: "2024-01-09 12:00:00",
            work_entry_type_request_unit: "hour",
        },
    ];
    await mountYearCalendar();

    await clickDate("2024-01-09");
    await waitFor(".o_cw_popover_holidays");
    expect(queryAllTexts(".o_cw_popover_holidays .fw-bold")).toEqual(["January 9, 2024"]);

    await clickDate("2024-01-10");
    expect(".o_cw_popover_holidays").toHaveCount(0);
});
