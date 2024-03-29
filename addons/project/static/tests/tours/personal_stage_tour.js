/** @odoo-module */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('personal_stage_tour', {
    test: true,
    url: '/web',
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
}, {
    content: "Open Pig Project",
    trigger: '.o_kanban_record:contains("Pig")',
}, {
    // Default is grouped by stage, user should not be able to create/edit a column
    content: "Check that there is no create column",
    trigger: "body:not(.o_column_quick_create)",
    run: function () {},
}, {
    content: "Check that there is no create column",
    trigger: "body:not(.o_column_edit)",
    run: function () {},
}, {
    content: "Check that there is no create column",
    trigger: "body:not(.o_column_delete)",
    run: function () {},
}, {
    content: "Go to tasks",
    trigger: 'button[data-menu-xmlid="project.menu_project_management"]',
},{
    content: "Go to my tasks", // My tasks is grouped by personal stage by default
    trigger: 'a[data-menu-xmlid="project.menu_project_management_my_tasks"]',
}, {
    content: "Check that we can create a new stage",
    trigger: '.o_column_quick_create .o_quick_create_folded'
}, {
    content: "Create a new personal stage",
    trigger: 'input.form-control',
    run: 'text Never',
}, {
    content: "Confirm create",
    trigger: '.o_kanban_add',
}, {
    content: "Check that column exists",
    trigger: '.o_kanban_header:contains("Never")',
    run: function () {},
}, {
    content: 'Open column edit dropdown',
    trigger: '.o_kanban_header:eq(0)',
    run: function () {
        document.querySelector('.o_kanban_config.dropdown .dropdown-toggle').dispatchEvent(new Event('click'));
    },
}, {
    content: "Try editing inbox",
    trigger: ".dropdown-item.o_column_edit",
}, {
    content: "Change title",
    trigger: 'div.o_field_char[name="name"] input',
    run: 'text  (Todo)',
}, {
    content: "Save changes",
    trigger: '.btn-primary:contains("Save")',
}, {
    content: "Check that column was updated",
    trigger: '.o_kanban_header:contains("Todo")',
}, {
    content: "Create a personal task from the quick create form",
    trigger: '.o-kanban-button-new',
}, {
    content: "Create a new personal task",
    trigger: 'input.o_input:not(.o_searchview_input)',
    run: 'text New Test Task',
}, {
    content: "Confirm create",
    trigger: '.o_kanban_add',
}, {
    content: "Check that task exists",
    trigger: '.o_kanban_record_title:contains("New Test Task")',
    run: function () {},
}]});
