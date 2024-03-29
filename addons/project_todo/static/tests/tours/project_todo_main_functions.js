/** @odoo-module */

import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('project_todo_main_functions', {
    test: true,
    url: '/web',
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="project_todo.menu_todo_todos"]',
}, {
    trigger: ".o_project_task_kanban_view .o_column_quick_create .o_kanban_add_column",
    content: "Create a personal stage from the To-do kanban view",
}, {
    trigger: ".o_project_task_kanban_view .o_column_quick_create .o_kanban_header input",
    extra_trigger: '.o_kanban_group',
    content: "Create a personal stage from the To-do kanban view",
    run: "edit Stage 1",
}, {
    trigger: ".o_project_task_kanban_view .o_column_quick_create .o_kanban_add",
    content: "Save the personal stage",
}, {
    trigger: ".o_project_task_kanban_view .o_column_quick_create .o_kanban_header input",
    extra_trigger: '.o_kanban_group',
    content: "Create a second personal stage from the To-do kanban view",
    run: "edit Stage 2",
}, {
    trigger: ".o_project_task_kanban_view .o_column_quick_create .o_kanban_add",
    content: "Save the personal stage",
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_group:eq(1)',
    content: "Create a task in the first stage",
}, {
    trigger: '.o_kanban_quick_create div.o_field_char[name=name] input',
    extra_trigger: '.o_project_task_kanban_view',
    content: "Create a personal task from the To-do kanban view",
    run: "edit Personal Task 1",
}, {
    trigger: '.o_kanban_quick_create .o_kanban_add',
    extra_trigger: '.o_project_task_kanban_view',
    content: "Save the personal task",
}, {
    trigger: ".o_kanban_record .oe_kanban_content",
    extra_trigger: '.o_project_task_kanban_view',
    content: "Drag &amp; drop the card to change the personal task from personal stage.",
    run: "drag_and_drop_native .o_kanban_group:eq(1) ",
}, {
    trigger: ".o_kanban_record:first",//:contains(Send message)
    extra_trigger: '.o_project_task_kanban_view',
    content: "Open the first todo record",
}, {
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-sendMessage",
    extra_trigger: '.o_todo_form_view',
    content: "A 'send message' button should be present in the chatter",
}, {
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-logNote",
    extra_trigger: '.o_todo_form_view',
    content: "A 'log note' button should be present in the chatter",
}, {
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-activity",
    extra_trigger: '.o_todo_form_view',
    content: "An 'Activities' button should be present in the chatter",
}, {
    trigger: "button[name=action_schedule_activities]",
    content: "Schedule an activity",
}, {
    trigger: ".o_field_widget[name='user_ids']",
    extra_trigger: '.o_todo_form_view',
    content: "Assign a responsible to your task",
    run() {
        document.querySelector('.o_field_widget[name="user_ids"] input').click();
    }
}, {
    trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
    auto: true,
}, {
    trigger: '.o_breadcrumb input.o_todo_breadcrumb_name_input',
    content: 'Edit the name of the personal task directly in the breadcrumb',
    run: "edit New name for the personal task",
}, {
    trigger: '.o_breadcrumb .o_todo_done_button',
    content: 'Mark the task as done directly from the breadcrumb',
}, {
    trigger: ".o_form_button_save",
    extra_trigger: '.o_todo_form_view .o_form_dirty',
    content: "Save the record",
}, {
    trigger: '.o_breadcrumb .o_control_panel_breadcrumbs_actions button',
    content: 'Convert the Todo to a task belonging to a project',
}, {
    trigger: '.o_menu_item:contains("Convert to Task")',
    content: "Click on the action menu 'Convert to task'",
}, {
    trigger: '.o_todo_conversion_form_view .o_field_many2one[name=project_id] input',
    content: 'Create a new project that will be set to the task',
    run: "edit Project test 1",
}, {
    trigger: '.o_todo_conversion_form_view .o_field_many2one[name=project_id] li.o_m2o_dropdown_option_create a',
    content: 'Create the new project',
}, {
    trigger: 'button[name="action_convert_to_task"]',
    content: 'Convert the todo to a task',
}, {
    trigger: ".breadcrumb-item:nth-child(1)",
    content: markup("Let's go back to the <b>kanban view</b> to have an overview of your next tasks."),
}, {
    trigger: ".o_kanban_view",
    isCheck: true,
}]});
