/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('hr_employee_tour', {
    test: true,
    url: '/web',
    steps: [
    stepUtils.showAppsMenuItem(),
    {
        content: "Open Employees app",
        trigger: ".o_app[data-menu-xmlid='hr.menu_hr_root']",
        run: 'click',
    },
    {
        content: "Open an Employee Profile",
        trigger: ".o_kanban_record_title:contains('Johnny H.')",
        run: 'click',
    },
    {
        content: "Open user account menu",
        trigger: ".o_user_menu .oe_topbar_name",
        run: 'click',
    }, {
        content: "Open My Profile",
        trigger: "[data-menu=settings]",
        run: 'click',
    },
]});
