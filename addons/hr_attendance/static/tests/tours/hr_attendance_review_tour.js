import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

/**
 * Click a counter and check that it filters the attendances of the given employee.
 */
function filterWithCounter(counter, employee) {
    return [
        {
            content: `Filter with the ${counter} counter`,
            trigger: `.o_attendance_kpi[name='${counter}']`,
            run: "click",
        },
        {
            trigger: `.o_attendance_kpi[name='${counter}'][aria-pressed='true']`,
        },
        {
            content: `${employee} is listed`,
            trigger: `.o_data_row:contains(${employee})`,
        },
    ];
}

const earlyRow = ".o_data_row:contains(Tour Early Employee)";
const stateCell = ".o_data_cell[name='state']";

registry.category("web_tour.tours").add("hr_attendance_review_tour", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open the Attendances app",
            trigger: ".o_app[data-menu-xmlid='hr_attendance.menu_hr_attendance_root']",
            run: "click",
        },
        {
            content: "Managers land on the overview",
            trigger: ".o_breadcrumb:contains(Overview)",
        },
        {
            content: "Open the attendances to review",
            trigger: "[data-menu-xmlid='hr_attendance.menu_hr_attendance_management_list']",
            run: "click",
        },
        {
            trigger: ".o_breadcrumb:contains(To Review)",
        },
        {
            content: "The same counters as on the overview, To Review selected",
            trigger: ".o_attendance_kpi[name='to_review'][aria-pressed='true']",
        },
        {
            content: "An attendance without exception was reviewed automatically",
            trigger: ".o_list_view:not(:has(.o_data_row:contains(Tour Regular Employee)))",
        },
        ...filterWithCounter("at_work", "Tour At Work Employee"),
        ...filterWithCounter("no_check_out", "Tour No Check-Out Employee"),
        ...filterWithCounter("overtime", "Tour Overtime Employee"),
        ...filterWithCounter("undertime", "Tour Undertime Employee"),
        ...filterWithCounter("late_check_in", "Tour Late Employee"),
        {
            content: "Open the late attendance",
            trigger: ".o_data_row:contains(Tour Late Employee) .o_data_cell[name='employee_id']",
            run: "click",
        },
        {
            content: "Approve it",
            trigger: ".o_form_view .o_statusbar_buttons button[name='action_validate']",
            run: "click",
        },
        {
            content: "The attendance is reviewed",
            trigger: ".o_statusbar_status button.o_arrow_button_current:contains(Reviewed)",
        },
        {
            content: "Back to the list",
            trigger: ".o_breadcrumb .breadcrumb-item a:contains(To Review)",
            run: "click",
        },
        ...filterWithCounter("early_check_out", "Tour Early Employee"),
        {
            content: "Refuse the early attendance from the list",
            trigger: ".o_data_row:contains(Tour Early Employee) button[name='action_refuse']",
            run: "click",
        },
        {
            content: "Refused, the attendance leaves the list",
            trigger: `.o_list_view:not(:has(${earlyRow} ${stateCell}:contains(To Review)))`,
        },
        {
            content: "The morning now ends the day early, and stays reviewed",
            trigger: `${earlyRow} ${stateCell}:contains(Reviewed)`,
        },
        {
            content: "Unselect the Early Clock Out counter",
            trigger: ".o_attendance_kpi[name='early_check_out'][aria-pressed='true']",
            run: "click",
        },
        {
            trigger: ".o_attendance_kpi[name='early_check_out'][aria-pressed='false']",
        },
        {
            content: "Show the refused attendances",
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            trigger: ".o_filter_menu .o-dropdown-item:contains(Refused)",
            run: "click",
        },
        {
            content: "Send the refused attendance back to review",
            trigger: `${earlyRow} button[name='action_reset_to_draft']`,
            run: "click",
        },
        ...filterWithCounter("to_review", "Tour Early Employee"),
        {
            content: "The attendance waits for review again",
            trigger: `${earlyRow} ${stateCell}:contains(To Review)`,
        },
    ],
});
