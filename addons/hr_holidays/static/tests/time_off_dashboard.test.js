import { describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { user } from "@web/core/user";
import { contains, defineModels, defineParams, fields, getService, models, mountView, mountWebClient, onRpc } from "@web/../tests/web_test_helpers";
import { clickDate } from "@web/../tests/views/calendar/calendar_test_helpers";
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
    hour_from = fields.Float();
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
    {has_accrual_allocation: true, allocation_data: {}, allocation_request_amount: 0}
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
    expect(`.fc-day.hr_mandatory_day_5[data-date="2025-03-17"]`).toHaveCount(1);
});

test(`test time rendering in foreign languages`, async () => {
    mockDate("2025-03-18 08:00:00");
    defineParams({
        lang: "nl",
    });
    HrLeave._views["form,hr_leave_view_form_dashboard_new_time_off"] = `
        <form>
            <field name="hour_from" widget="float_time_selection"/>
        </form>
    `;
    await mountView({
        type: "calendar",
        resModel: "hr.leave",
        context: user.context,
    });
    await clickDate("2025-03-18");
    await contains(".o_field_widget[name='hour_from'] input").click();
    await contains(".o_popover select:nth-of-type(1)").select("14");
    await contains(".o_popover select:nth-of-type(2)").select("30");
    await contains(".modal-content").click();  // Confirm selection
    await expect("div[name='hour_from'] input").toHaveValue("2:30 p.m.");
})
