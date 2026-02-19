import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("load_employee_sample_data_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Employees app",
            trigger: ".o_app[data-menu-xmlid='hr.menu_hr_root']",
            run: "click",
        },
        {
            content: "Click on 'Load Sample data' button",
            trigger: "a#loadSampleDataBtn",
            run: "click",
            expectUnloadPage: true,
        },
    ],
});
