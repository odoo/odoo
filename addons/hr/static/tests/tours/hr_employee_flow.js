/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('hr_employee_tour', {
    url: '/odoo',
    steps: () => [
    stepUtils.showAppsMenuItem(),
    {
        content: "Open Employees app",
        trigger: ".o_app[data-menu-xmlid='hr.menu_hr_root']",
        run: 'click',
    },
    {
        content: "Open an Employee Profile",
        trigger: ".o_kanban_record:contains('Johnny H.')",
        run: 'click',
    },
    {
        content: "Open user account menu",
        trigger: ".o_user_menu .dropdown-toggle",
        run: 'click',
    }, {
        content: "Open My Profile",
        trigger: "[data-menu=settings]",
        run: 'click',
    },
]});

registry.category("web_tour.tours").add("hr_candidate_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "Open Recruitment App",
            trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
            run: "click",
        },
        {
            content: "Open Applications menu",
            trigger: 'button.dropdown-toggle:contains("Applications")',
            run: "click",
        },
        {
            content: "Go to Candidates list",
            trigger: 'a.dropdown-item:contains("Candidates")',
            run: "click",
        },
        {
            content: "Click on candidate",
            trigger: '.o_kanban_record:contains("Extended Test Candidate")',
            run: "click",
        },
        {
            content: "Candidate form should open",
            trigger: ".o_form_view", // Wait for form view container
        },
        {
            trigger: 'button[title="Toggle Studio"]',
            run: "click",
        },
        {
            trigger: ".nav-link.o_web_studio_view",
            run: "click",
        },
        {
            content: "Show invisible elements",
            trigger: 'label[for="show_invisible"]',
            run: "click",
        },
    ],
});
