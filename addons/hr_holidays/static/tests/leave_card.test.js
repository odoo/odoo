import { HrLeave } from "@hr_holidays/../tests/mock_server/mock_models/hr_leave";
import { ResUsers } from "@hr_holidays/../tests/mock_server/mock_models/res_users";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { mountView, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { clickDate } from "@web/../tests/views/calendar/calendar_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { click, waitFor } from "@odoo/hoot-dom";
import { user } from "@web/core/user";

describe.current.tags("desktop");
defineHrHolidaysModels();

test("Test request creator buttons", async() => {
    mockDate("2024-01-03 12:00:00", 0);
    patchWithCleanup(user, { userId: 100 });

    HrLeave._views = {
         "form,hr_leave_view_form_dashboard_new_time_off": `
            <form>
                <field name="state"/>
                <field name="holiday_status_id"/>
                <field name="employee_id"/>
                <field name="user_id"/>
                <field name="can_cancel"/>
            </form>
        `,
    };

    HrLeave._records = [
        {
            'id': 1, 'state': 'confirm', 'holiday_status_id': 55, 'employee_id': 100,
            'user_id': 100, 'date_from': '2024-01-09 09:00:00', 'date_to': '2024-01-09 18:00:00'
        },
        {
            'id': 2, 'state': 'validate1', 'holiday_status_id': 55, 'employee_id': 100,
            'can_cancel': true, 'user_id': 100, 'date_from': '2024-01-10 09:00:00', 'date_to': '2024-01-10 18:00:00'
        },
    ]

    ResUsers._records = [
        ...ResUsers._records,
        { 'id': 100, 'name': "User 1", 'employee_id': 100 },
    ]

    onRpc("get_mandatory_days", () => ({}));
    onRpc("get_unusual_days", () => ({}));
    onRpc("get_allocation_data_request", () => ({}));
    onRpc("get_special_days_data", () => ({bankHolidays: [], mandatoryDays: []}));
    onRpc("hr.employee", "get_time_off_dashboard_data", () => (
        {has_accrual_allocation: true, allocation_data: {}, allocation_request_amount: 0}
    ));

    await mountView({
            type: "calendar",
            resModel: "hr.leave",
            arch: `
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
            </calendar>`,
            context: user.context
        });
    await clickDate("2024-01-09");
    await click(".o_cw_popover_link");
    await waitFor("button:contains(Delete Time Off)");
    await click(".btn-close");
    await clickDate("2024-01-10");
    await click(".o_cw_popover_link");
    await waitFor("button:contains(Cancel Time Off)");
})

