import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { HrLeave } from "@hr_holidays/../tests/mock_server/mock_models/hr_leave";
import { ResUsers } from "@hr_holidays/../tests/mock_server/mock_models/res_users";
import { describe, expect, test } from "@odoo/hoot";
import { click, press, queryAll, waitFor } from "@odoo/hoot-dom";
import { mockDate, runAllTimers } from "@odoo/hoot-mock";
import { clickDate } from "@web/../tests/views/calendar/calendar_test_helpers";
import { mountView, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";

describe.current.tags("desktop");
defineHrHolidaysModels();

const CALENDAR_ARCH = `
    <calendar js_class="time_off_calendar_dashboard"
            string="Time Off Request"
            form_view_id="hr_leave_view_form_dashboard_new_time_off"
            event_open_popup="true"
            date_start="date_from"
            date_stop="date_to"
            quick_create="0"
            show_date_picker="0"
            show_unusual_days="True"
            hide_time="True"
            mode="year">
        <field name="display_name" string=""/>
        <field name="holiday_status_id" filters="1" invisible="1" color="color"/>
        <field name="state" invisible="1"/>
        <field name="is_hatched" invisible="1" />
        <field name="is_striked" invisible="1"/>
    </calendar>`;

/** The pending request an approver sees: they may approve it and refuse it. */
function setupApprovableLeave() {
    mockDate("2024-01-03 12:00:00", 0);
    patchWithCleanup(user, { userId: 100 });

    HrLeave._views = {
        "form,hr_leave_view_form_dashboard_new_time_off": `
            <form>
                <field name="state"/>
                <field name="holiday_status_id"/>
                <field name="employee_id"/>
                <field name="user_id"/>
                <field name="can_approve"/>
                <field name="can_refuse"/>
            </form>
        `,
    };
    HrLeave._records = [
        {
            id: 1,
            state: "confirm",
            holiday_status_id: 55,
            employee_id: 200,
            user_id: 200,
            can_approve: true,
            can_refuse: true,
            date_from: "2024-01-09 09:00:00",
            date_to: "2024-01-09 18:00:00",
        },
    ];
    ResUsers._records = [
        ...ResUsers._records,
        { id: 100, name: "The approver", employee_id: 100 },
        { id: 200, name: "The requester", employee_id: 200 },
    ];

    onRpc("get_mandatory_days", () => ({}));
    onRpc("get_unusual_days", () => ({}));
    onRpc("get_allocation_data_request", () => ({}));
    onRpc("get_special_days_data", () => ({ bankHolidays: [], mandatoryDays: [] }));
    onRpc("hr.employee", "get_time_off_dashboard_data", () => ({
        has_accrual_allocation: true,
        allocation_data: {},
        allocation_request_amount: 0,
    }));
}

async function openTheRequestDialog() {
    await mountView({
        type: "calendar",
        resModel: "hr.leave",
        arch: CALENDAR_ARCH,
        context: user.context,
    });
    await clickDate("2024-01-09");
    await click(".o_cw_popover_link");
    await waitFor(".modal button:contains(Refuse)");
}

test("every button of the request dialog owns its hotkey", async () => {
    setupApprovableLeave();
    await openTheRequestDialog();

    const hotkeys = queryAll(".modal [data-hotkey]").map((button) =>
        button.dataset.hotkey.toLowerCase(),
    );
    expect(hotkeys.length).toBeGreaterThan(1);
    expect([...new Set(hotkeys)]).toHaveLength(hotkeys.length, {
        message:
            "two buttons sharing a hotkey means one of them can never be reached: " +
            "the service keeps the first match in the DOM and drops the rest",
    });
});

test("the Refuse hotkey refuses instead of approving", async () => {
    setupApprovableLeave();
    onRpc("hr.leave", "action_approve", () => {
        expect.step("action_approve");
        return false;
    });
    onRpc("hr.leave", "action_refuse", () => {
        expect.step("action_refuse");
        return false;
    });
    await openTheRequestDialog();

    const refuse = queryAll(".modal button").find(
        (button) => button.textContent.trim() === "Refuse",
    );
    await press(["alt", refuse.dataset.hotkey]);
    await runAllTimers();

    expect.verifySteps(["action_refuse"]);
});
