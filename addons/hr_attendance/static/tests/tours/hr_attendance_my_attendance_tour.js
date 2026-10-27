import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("hr_attendance_my_attendance_tour", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open the Attendances app",
            trigger: ".o_app[data-menu-xmlid='hr_attendance.menu_hr_attendance_root']",
            run: "click",
        },
        {
            content: "The app opens the check in panel of the systray: open my attendances",
            trigger: ".att_container .o_wrap_btn_sign_out button[name='my_attendances']",
            run: "click",
        },
        {
            content: "Open my last attendance, listed without the counters",
            trigger: ".o_list_view:not(:has(.o_attendance_dashboard)) .o_data_row:first-child .o_data_cell",
            run: "click",
        },
        {
            content: "The attendance is reviewed",
            trigger: ".o_statusbar_status button.o_arrow_button_current:contains(Reviewed)",
        },
        {
            content: "Users see neither the chatter nor the logs",
            trigger: ".o_form_view:not(:has(.o-mail-Chatter)):not(:has(.o_notebook)) .o_field_widget[name='break_duration'] input",
            run: "edit 0:30",
        },
        {
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "The changed attendance goes back to review",
            trigger: ".o_statusbar_status button.o_arrow_button_current:contains(To Review)",
        },
    ],
});
