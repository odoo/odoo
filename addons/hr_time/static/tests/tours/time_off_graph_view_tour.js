import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("time_off_graph_view_tour", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: ".o_app[data-menu-xmlid='hr_time.menu_hr_time_root']",
            run: "click",
        },
        {
            trigger: ".fc-daygrid-day-top",
        },
        {
            content: "Open reporting menu",
            trigger: ".o-dropdown[data-menu-xmlid='hr_time.menu_hr_time_report']",
            run: "click",
        },
        {
            content: "Open reporting by type",
            trigger: ".o-dropdown-item[data-menu-xmlid='hr_time.menu_hr_time_summary_all']",
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
