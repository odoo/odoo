import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('project_todo_main_functions', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="project_todo.menu_todo_todos"]',
    run: "click",
}, {
    trigger: ".o_project_task_kanban_view .o_column_quick_create.o_quick_create_folded div",
    content: "Create a personal stage from the To-do kanban view",
    run: "click",
},
{
    trigger: ".o_kanban_group",
},
{
    trigger: ".o_project_task_kanban_view .o_column_quick_create .o_kanban_header input",
    content: "Create a personal stage from the To-do kanban view",
    run: "edit Stage 1",
}, {
    trigger: ".o_project_task_kanban_view .o_column_quick_create .o_kanban_add",
    content: "Save the personal stage",
    run: "click",
},
{
    trigger: ".o_kanban_group",
},
{
    trigger: ".o_project_task_kanban_view .o_column_quick_create .o_kanban_header input",
    content: "Create a second personal stage from the To-do kanban view",
    run: "edit Stage 2",
}, {
    trigger: ".o_project_task_kanban_view .o_column_quick_create .o_kanban_add",
    content: "Save the personal stage",
    run: "click",
},
{
    trigger: ".o_kanban_group:eq(1)",
},
{
    trigger: '.o-kanban-button-new',
    content: "Create a task in the first stage",
    run: "click",
},
{
    trigger: ".o_project_task_kanban_view",
},
{
    trigger: '.o_kanban_quick_create div.o_field_char[name=display_name] input',
    content: "Create a personal task from the To-do kanban view",
    run: "edit Personal Task 1",
},
{
    trigger: ".o_project_task_kanban_view",
},
{
    trigger: '.o_kanban_quick_create .o_kanban_add',
    content: "Save the personal task",
    run: "click",
},
{
    trigger: ".o_project_task_kanban_view",
},
{
    trigger: ".o_kanban_record",
    content: "Drag &amp; drop the card to change the personal task from personal stage.",
    run: "drag_and_drop(.o_kanban_group:eq(1))",
},
{
    trigger: ".o_project_task_kanban_view",
},
{
    content: "Click on invisible caret. Should hover on card to be visible",
    trigger: ".o_dropdown_kanban .btn.o-no-caret:not(:visible)",
    run: "click",
}, {
    trigger: "a:contains('Set Cover Image')",
}, {
    trigger: ".o_kanban_record:first",//:contains(Send message)
    content: "Open the first todo record",
    run: "click",
},
{
    trigger: ".o_todo_form_view",
},
{
    trigger: ".todo_toggle_chatter",
    content: "Clicking on the chatter button should toggle open the chatter",
    run: "click",
},
{
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-sendMessage",
    content: "A 'send message' button should be present in the chatter",
    run: "click",
},
{
    trigger: ".o_todo_form_view",
},
{
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-logNote",
    content: "A 'log note' button should be present in the chatter",
    run: "click",
},
{
    trigger: ".o_todo_form_view",
},
{
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-activity",
    content: "An 'Activities' button should be present in the chatter",
    run: "click",
}, {
    trigger: "button[name=action_schedule_activities]",
    content: "Schedule an activity",
    run: "click",
},
{
    trigger: ".o_todo_form_view",
},
{
    trigger: ".o_field_widget[name='user_ids'] input",
    content: "Assign a responsible to your task",
    run: "fill marc",
},
{
    isActive: ["auto"],
    trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
    run: "click",
}, {
    trigger: '.o_field_widget[name="name"] textarea',
    content: 'Edit the name of the personal task',
    run: "edit New name for the personal task",
}, {
    trigger: '.o_todo_done_button',
    content: 'Mark the task as done',
    run: "click",
},
{
    trigger: ".o_todo_form_view .o_form_dirty",
},
{
    trigger: ".o_form_button_save",
    content: "Save the record",
    run: "click",
}, {
    trigger: '.o_breadcrumb .o_control_panel_breadcrumbs_actions button:enabled',
    content: "Convert the Todo to a task belonging to a project:enabled",
    run: "click",
}, {
    trigger: '.o_menu_item:contains("Convert to Task")',
    content: "Click on the action menu 'Convert to task'",
    run: "click",
}, {
    trigger: '.o_todo_conversion_form_view .o_field_many2one[name=project_id] input',
    content: 'Create a new project that will be set to the task',
    run: "edit Project test 1",
}, {
    trigger: '.o_todo_conversion_form_view .o_field_many2one[name=project_id] li.o_m2o_dropdown_option_create a',
    content: 'Create the new project',
    run: "click",
}, {
    trigger: 'button[name="action_convert_to_task"]',
    content: 'Convert the todo to a task',
    run: "click",
}, {
    trigger: ".o_form_view .breadcrumb-item:nth-child(1)",
    content: markup`Let's go back to the <b>kanban view</b> to have an overview of your next tasks.`,
    run: "click",
}, {
    trigger: ".o_kanban_view",
}]});
