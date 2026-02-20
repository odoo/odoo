import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

const leaveType = "Overtime Compensation No Allocation";
const leaveDateFrom = "01/04/2021";
const leaveDateTo = "01/04/2021";

registry.category("web_tour.tours").add("request_overtime_leave_from_attendance_calendar", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Employees app",
            trigger: ".o_app[data-menu-xmlid='hr.menu_hr_root']",
            run: "click",
        },
        {
            content: "Open an Employee Profile",
            trigger: ".o_kanban_record:contains('Barnabé')",
            run: "click",
        },
        {
            content: "Open Monthly Hours smart button",
            trigger: ".oe_stat_button:contains('Monthly Hours')",
            run: "click",
        },
        {
            content: "Switch to Calendar View",
            trigger: ".o_switch_view.o_calendar",
            run: "click",
        },
        {
            content: "Click on New Timeoff Request",
            trigger: ".o_attendance_info_link:contains('NEW TIMEOFF REQUEST')",
            run: "click",
        },
        {
            content: "Select Overtime Compensation No Allocation as Leave Type",
            trigger: "div[name='work_entry_type_id'] input",
            run: `edit ${leaveType}`,
        },
        {
            content: "Wait for the autocomplete and select the leave type",
            trigger: `.ui-autocomplete .ui-menu-item a:contains("${leaveType}")`,
            run: "click",
        },
        {
            content: "Click on the start date of the leave",
            trigger: "div[name=request_date_from] button",
            run: "click",
        },
        {
            content: "Select the start date of the leave",
            trigger: "input[data-field=request_date_from]",
            run: `edit ${leaveDateFrom}`,
        },
        {
            content: "Click on the end date of the leave",
            trigger: "button[data-field=request_date_to]",
            run: "click",
        },
        {
            content: "Select the end date of the leave",
            trigger: "input[data-field=request_date_to]",
            run: `edit ${leaveDateTo} && press Enter`,
        },
        {
            content: "Save the leave",
            trigger: '.btn:contains("Submit Request")',
            run: "click",
        },
        {
            content: "Ensure Form is properly saved and closed",
            trigger: "body:not(:has(.o_hr_leave_form))"
        }
    ],
});
