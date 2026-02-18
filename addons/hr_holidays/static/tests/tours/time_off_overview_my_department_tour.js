import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("time_off_overview_my_department_tour", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            run: "click",
        },
        {
            content: "Open Overview menu",
            trigger: ".o-dropdown-item[data-menu-xmlid='hr_holidays\\.menu_hr_holidays_dashboard']",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Click on the search bar",
            trigger: ".o_searchview_input",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Select 'My Department' filter",
            trigger: ".o_dropdown_container:nth-child(1) > .o-dropdown-item:nth-child(3)",
            run: "click",
            tooltipPosition: "bottom",
        },
        {
            content: "Ensure the 'My Department' filter is applied with no access errors",
            trigger: "body:not(:has(.o_error_dialog))",  
        },
    ],
});

