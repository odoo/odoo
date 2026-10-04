import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('project_tour_test', {
    steps: () => [stepUtils.showAppsMenuItem(), {
    isActive: ["community"],
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    content: 'Want a better way to manage your projects? It starts here.',
    run: "click",
}, {
    isActive: ["enterprise"],
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    content: 'Want a better way to manage your projects? It starts here.',
    run: "click",
},
{
    trigger: ".o_project_kanban",
},
{
    trigger: '.o-kanban-button-new',
    content: 'Let\'s create your first project.',
    run: "click",
}, {
    isActive: ['.o-kanban-button-new.dropdown'], // if the project template dropdown is active
    trigger: 'button.o-dropdown-item:contains("New Project")',
    content: 'Let\'s create a regular project.',
    run: "click",
}, {
    trigger: '.o_project_name input',
    content: 'Choose a name for your project. It can be anything you want: the name of a customer, of a product, of a team, of a construction site, etc.',
    run: "edit Test",
}, {
    trigger: '.o_open_tasks',
    content: 'Let\'s create your first project.',
    run: "click .modal:visible .btn.btn-primary",
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_header input",
    content: "Add columns to organize your tasks into stages e.g. New - In Progress - Done.",
    run: "edit Test",
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    content: 'Let\'s create your first stage.',
    run: "click",
},
{
    trigger: ".o_kanban_group",
},
{
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_header input",
    content: "Add columns to organize your tasks into stages e.g. New - In Progress - Done.",
    run: "edit Test",
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    content: 'Let\'s create your second stage.',
    run: "click",
},
{
    trigger: ".o_kanban_group:eq(1)",
},
{
    trigger: '.o-kanban-button-new',
    content: "Let's create your first task.",
    run: "click",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: '.o_kanban_quick_create div.o_field_char[name=display_name] input',
    content: 'Choose a task name (e.g. Website Design, Purchase Goods...)',
    run: "edit Test",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: '.o_kanban_quick_create .o_kanban_add',
    content: "Add your task once it is ready.",
    run: "click",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: ".o_kanban_record",
    content: "Drag & drop the card to change your task from stage.",
    run: "drag_and_drop(.o_kanban_group:eq(1))",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: ".o_kanban_record:first",
    content: "Let's start working on your task.",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-sendMessage",
    content: "Use the chatter to send emails and communicate efficiently with your customers. Add new people to the followers' list to make them aware of the main changes about this task.",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: "button.o-mail-Chatter-logNote",
    content: "Log internal notes and use @mentions to notify your colleagues.",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-activity",
    content: "Create activities to set yourself to-dos or to schedule meetings.",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: ".modal-dialog .btn-primary",
    content: "Schedule your activity once it is ready.",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: ".o_field_widget[name='user_ids'] input",
    content: "Assign a responsible to your task",
    run: "edit Admin",
},
{
    isActive: ["desktop"],
    trigger: "a.dropdown-item[id*='user_ids'] span",
    content: "Select an assignee from the menu",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: "div.o_kanban_renderer > article.o_kanban_record",
    run: "click",
}, {
    trigger: 'button[name="sub_tasks_page"]',
    content: 'Open sub-tasks notebook section',
    run: 'click',
}, {
    trigger: '.o_field_subtasks_one2many .o_list_renderer .o_field_x2many_list_row_add button',
    content: 'Add a sub-task',
    run: 'click',
}, {
    trigger: '.o_field_subtasks_one2many div[name="name"] input',
    content: 'Give the sub-task a name',
    run: "edit New Sub-task",
},
{
    trigger: ".o_form_project_tasks .o_form_dirty",
},
{
    trigger: ".o_form_button_save",
    content: "You have unsaved changes - no worries! Odoo will automatically save it as you navigate. You can discard these changes from here or manually save your task. Let's save it manually.",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: ".o_breadcrumb .o_back_button",
    content: "Let's go back to the kanban view to have an overview of your next tasks.",
    run: 'click',
}, {
    trigger: ".o_kanban_record .o_widget_subtask_counter .subtask_list_button",
    content: "You can open sub-tasks from the kanban card!",
    run: "click",
},
{
    trigger: ".o_widget_subtask_kanban_list .subtask_list",
},
{
    trigger: ".o_kanban_record .o_widget_subtask_kanban_list .subtask_create",
    content: "Create a new sub-task",
    run: "click",
},
{
    trigger: ".subtask_create_input",
},
{
    trigger: ".o_kanban_record .o_widget_subtask_kanban_list .subtask_create_input input",
    content: "Give the sub-task a name",
    run: "edit Newer Sub-task && click body",
}, {
    trigger: ".o_kanban_record .o_widget_subtask_kanban_list .subtask_list_row:contains(newer sub-task) .o_field_project_task_state_selection button",
    content: "You can change the sub-task state here!",
    run: "click",
},
{
    trigger: ".project_task_state_selection_menu.dropdown-menu",
},
{
    trigger: ".project_task_state_selection_menu.dropdown-menu span.text-danger",
    content: "Mark the task as Cancelled",
    run: "click",
}, {
    trigger: ".o-overlay-container:not(:visible):not(:has(.project_task_state_selection_menu))",
}, {
    trigger: ".o_kanban_record .o_widget_subtask_counter .subtask_list_button:contains('1/2')",
    content: "Close the sub-tasks list",
    run: "click",
}, {
    trigger: '.o_kanban_renderer',
    // last step to confirm we've come back before considering the tour successful
    run: "click",
}]});
