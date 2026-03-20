import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("time_off_graph_view_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: ".o_app[data-menu-xmlid='hr_holidays.menu_hr_holidays_root']",
            run: "click",
        },
        {
            trigger: ".fc-daygrid-day-top",
        },
        {
            content: "Open reporting menu",
            trigger: ".o-dropdown[data-menu-xmlid='hr_holidays.menu_hr_holidays_report']",
            run: "click",
        },
        {
            content: "Open reporting by type",
            trigger: ".o-dropdown-item[data-menu-xmlid='hr_holidays.menu_hr_holidays_summary_all']",
            run: "click",
        },
        {
            trigger: ".o_graph_canvas_container",
        },
        {
            content: "Open bar chart view",
            trigger: "button[data-mode='bar']",
            run: "click",
        },
    ],
});
