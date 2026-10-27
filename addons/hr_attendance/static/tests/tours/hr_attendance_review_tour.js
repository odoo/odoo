import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("hr_attendance_review_tour", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open the Attendances app",
            trigger: ".o_app[data-menu-xmlid='hr_attendance.menu_hr_attendance_root']",
            run: "click",
        },
        {
            content: "Managers land on the dashboard",
            trigger: ".o_breadcrumb:contains(Dashboard)",
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
            content: "The same counters as on the dashboard, To Review selected",
            trigger: ".o_attendance_kpi[name='to_review'][aria-pressed='true']",
        },
        {
            trigger: ".o_attendance_kpi[name='at_work']",
        },
        {
            content: "Filter the late check-ins with their counter",
            trigger: ".o_attendance_kpi[name='late_check_in']",
            run: "click",
        },
        {
            trigger: ".o_attendance_kpi[name='late_check_in'][aria-pressed='true']",
        },
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
    ],
});
