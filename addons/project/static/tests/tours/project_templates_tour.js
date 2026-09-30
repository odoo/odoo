import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("project_templates_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
            run: "click",
        },
        {
            content: "Click on New Button of Kanban view",
            trigger: ".o-kanban-button-new",
            run: "click",
        },
        {
            trigger: '.dropdown-menu button.dropdown-item:contains("Project Template")',
            run: "click",
            content: "Create a project from the template",
        },
        {
            trigger: '.modal div[name="name"] .o_input',
            run: "edit New Project",
        },
        {
            trigger: 'button[name="create_project_from_template"]',
            run: "click",
        },
        {
            content: "Go back to kanban view",
            trigger: ".breadcrumb-item a:contains('Projects')",
            run: "click",
        },
        {
            content: "Check for created project",
            trigger: ".o_kanban_record:contains('New Project')",
        },
        {
            content: "Go to list view",
            trigger: "button.o_switch_view.o_list",
            run: "click",
        },
        {
            content: "Click on New Button of List view",
            trigger: ".o_list_button_add",
            run: "click",
        },
        {
            content: "Lets Create a second project from the template",
            trigger: '.dropdown-menu button.dropdown-item:contains("Project Template")',
            run: "click",
        },
        {
            trigger: '.modal div[name="name"] .o_input',
            run: "edit New Project 2",
        },
        {
            trigger: 'button[name="create_project_from_template"]',
            run: "click",
        },
        {
            content: "Go back to list view",
            trigger: ".breadcrumb-item a:contains('Projects')",
            run: "click",
        },
        {
            content: "Check for created project",
            trigger: ".o_data_row td[name='name']:contains('New Project 2')",
        },
    ],
});
