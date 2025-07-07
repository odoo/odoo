import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('personal_stage_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    run: "click",
}, {
    content: "Open Pig Project",
    trigger: '.o_kanban_record:contains("Pig")',
    run: "click",
}, {
    // Default is grouped by stage, user should not be able to create/edit a column
    content: "Check that there is no create column",
    trigger: "body:not(.o_column_quick_create)",
}, {
    content: "Check that there is no create column",
    trigger: "body:not(.o_group_edit)",
}, {
    content: "Check that there is no create column",
    trigger: "body:not(.o_group_delete)",
}, {
    content: "Go to tasks",
    trigger: 'button[data-menu-xmlid="project.menu_project_management"]',
    run: "click",
},{
    content: "Go to my tasks", // My tasks is grouped by personal stage by default
    trigger: 'a[data-menu-xmlid="project.menu_project_management_my_tasks"]',
    run: "click",
}, {
    content: "Check that we can create a new stage",
    trigger: '.o_column_quick_create.o_quick_create_folded div',
    run: "click",
}, {
    content: "Create a new personal stage",
    trigger: 'input.form-control',
    run: "edit Never",
}, {
    content: "Confirm create",
    trigger: '.o_kanban_add',
    run: "click",
}, {
    content: "Check that column exists && Open column edit dropdown",
    trigger: ".o_kanban_header:contains(Never)",
    run: "hover && click .o_kanban_header:contains(Never) .dropdown-toggle",
}, {
    content: "Try editing inbox",
    trigger: ".dropdown-item.o_group_edit",
    run: "click",
}, {
    content: "Change title",
    trigger: 'div.o_field_char[name="name"] input',
    run: "edit ((Todo))",
}, {
    content: "Save changes",
    trigger: '.btn-primary:contains("Save")',
    run: "click",
}, {
    content: "Check that column was updated",
    trigger: '.o_kanban_header:contains("Todo")',
    run: "click",
}, {
    content: "Create a personal task from the quick create form",
    trigger: '.o-kanban-button-new',
    run: "click",
}, {
    content: "Create a new personal task",
    trigger: 'input.o_input:not(.o_searchview_input)',
    run: "edit New Test Task",
}, {
    content: "Confirm create",
    trigger: '.o_kanban_add',
    run: "click",
}, {
    content: "Check that task exists",
    trigger: '.o_kanban_record:contains("New Test Task")',
}]});
