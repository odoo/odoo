import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("time_off_request_calendar_view", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            run: "click",
        },
        {
            content: "Click on the first Thursday of the year",
            trigger: ".fc-daygrid-day.fc-day-thu .fc-daygrid-day-number",
            run: "click",
        },
        {
            content: "Save the leave",
            trigger: '.o_form_button_save',
            run: "click",
        },
    ],
});
