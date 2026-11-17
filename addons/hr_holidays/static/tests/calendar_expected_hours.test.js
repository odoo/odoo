import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { mountView, onRpc } from "@web/../tests/web_test_helpers";
import { changeScale, toggleFilter } from "@web/../tests/views/calendar/calendar_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { HrLeave } from "@hr_holidays/../tests/mock_server/mock_models/hr_leave";

describe.current.tags("desktop");
defineHrHolidaysModels();

async function mountMonthCalendar(expectedHours) {
    onRpc("get_expected_hours", () => expectedHours);
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
                      mode="month">
                <field name="display_name" string=""/>
                <field name="work_entry_type_id" filters="1" invisible="1" color="color"/>
                <field name="state" invisible="1"/>
            </calendar>`,
    });
}

const badge = (date) => `.o_calendar_day[data-date="${date}"] .o_expected_hours`;
// the badge is hidden until the cell is hovered, so its rendered text is empty
const badgeText = (date) => queryOne(badge(date)).textContent;

test("expected hours badge follows a reload of the same range", async () => {
    mockDate("2024-01-03 12:00:00", 0);
    HrLeave._records = [
        {
            id: 1,
            employee_id: 100,
            state: "validate",
            date_from: "2024-01-16 00:00:00",
            date_to: "2024-01-17 00:00:00",
            work_entry_type_id: 55,
            work_entry_type_request_unit: "day",
        },
        {
            id: 2,
            employee_id: 100,
            state: "validate",
            date_from: "2024-01-23 00:00:00",
            date_to: "2024-01-24 00:00:00",
            work_entry_type_id: 65,
            work_entry_type_request_unit: "day",
        },
    ];
    const expectedHours = { "2024-01-08": 8, "2024-01-09": 4.5 };
    await mountMonthCalendar(expectedHours);

    expect(badgeText("2024-01-08")).toBe("8h");
    expect(badgeText("2024-01-09")).toBe("4h 30m");
    expect(badge("2024-01-10")).toHaveCount(0);

    // e.g. a time off was approved on the 8th: the same range reloads without remounting the cells
    delete expectedHours["2024-01-08"];
    await toggleFilter("work_entry_type_id", "65");
    expect(badge("2024-01-08")).toHaveCount(0);
    expect(badgeText("2024-01-09")).toBe("4h 30m");
});

test("expected hours badge is only shown on the month grid", async () => {
    mockDate("2024-01-08 12:00:00", 0);
    HrLeave._records = [];
    await mountMonthCalendar({ "2024-01-08": 8 });
    expect(".o_expected_hours").toHaveCount(1);

    await changeScale("week");
    expect(".o_expected_hours").toHaveCount(0);
});
