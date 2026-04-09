import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("project_task_templates_tour", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
            run: "click",
        },
        {
            trigger: '.o_kanban_record span:contains("Project with Task Template")',
            run: "click",
            content: "Navigate to the project with a task template",
        },
        {
            trigger: 'div.o_last_breadcrumb_item span:contains("Project with Task Template")',
            content: "Wait for the kanban view to load",
        },
        {
            trigger: ".o-kanban-button-new",
            run: "click",
        },
        {
            trigger: '.dropdown-menu button.dropdown-item:contains("Template")',
            run: "click",
            content: "Create a task with the template",
        },
        {
            trigger: 'div[name="name"] .o_input',
            run: "edit Task",
        },
        ...stepUtils.saveForm(),
        {
            trigger: 'div.note-editable.odoo-editor-editable:contains("Template description")',
            content: "Check that the created task has copied the description of the template",
        },
    ],
});
