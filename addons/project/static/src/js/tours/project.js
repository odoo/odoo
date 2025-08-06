import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('project_tour', {
    url: "/odoo",
    steps: () => [stepUtils.showAppsMenuItem(), {
    isActive: ["community"],
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    content: markup(_t('Want a better way to <b>manage your projects</b>? <i>It starts here.</i>')),
    tooltipPosition: 'right',
    run: "click",
}, {
    isActive: ["enterprise"],
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    content: markup(_t('Want a better way to <b>manage your projects</b>? <i>It starts here.</i>')),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: ".o_project_kanban",
},
{
    trigger: '.o-kanban-button-new',
    content: markup(_t('Let\'s create your first <b>project</b>.')),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: '.o_project_name input',
    content: markup(_t('Choose a <b>name</b> for your project. <i>It can be anything you want: the name of a customer, of a product, of a team, of a construction site, etc.</i>')),
    tooltipPosition: 'right',
    run: "edit Test",
}, {
    trigger: '.o_open_tasks',
    content: markup(_t('Let\'s create your first <b>project</b>.')),
    tooltipPosition: 'top',
    run: "click .modal:visible .btn.btn-primary",
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_header input",
    content: markup(_t("Add columns to organize your tasks into <b>stages</b> <i>e.g. New - In Progress - Done</i>.")),
    tooltipPosition: 'bottom',
    run: "edit Test",
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    content: markup(_t('Let\'s create your first <b>stage</b>.')),
    tooltipPosition: 'right',
    run: "click",
},
{
    trigger: ".o_kanban_group",
},
{
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_header input",
    content: markup(_t("Add columns to organize your tasks into <b>stages</b> <i>e.g. New - In Progress - Done</i>.")),
    tooltipPosition: 'bottom',
    run: "edit Test",
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    content: markup(_t('Let\'s create your second <b>stage</b>.')),
    tooltipPosition: 'right',
    run: "click",
},
{
    trigger: ".o_kanban_group:eq(1)",
},
{
    trigger: '.o-kanban-button-new',
    content: markup(_t("Let's create your first <b>task</b>.")),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: '.o_kanban_quick_create div.o_field_char[name=display_name] input',
    content: markup(_t('Choose a task <b>name</b> <i>(e.g. Website Design, Purchase Goods...)</i>')),
    tooltipPosition: 'right',
    run: "edit Test",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: '.o_kanban_quick_create .o_kanban_add',
    content: _t("Add your task once it is ready."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: ".o_kanban_record",
    content: markup(_t("<b>Drag &amp; drop</b> the card to change your task from stage.")),
    tooltipPosition: "bottom",
    run: "drag_and_drop(.o_kanban_group:eq(1))",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: ".o_kanban_record:first",
    content: _t("Let's start working on your task."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-sendMessage",
    content: markup(_t("Use the chatter to <b>send emails</b> and communicate efficiently with your customers. Add new people to the followers' list to make them aware of the main changes about this task.")),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: "button.o-mail-Chatter-logNote",
    content: markup(_t("<b>Log internal notes</b> and use @<b>mentions</b> to notify your colleagues.")),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-activity",
    content: markup(_t("Create <b>activities</b> to set yourself to-dos or to schedule meetings.")),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: ".modal-dialog .btn-primary",
    content: _t("Schedule your activity once it is ready."),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    isActive: ["auto"],
    trigger: ".o_field_widget[name='user_ids'] input",
    content: _t("Assign a responsible to your task"),
    tooltipPosition: "right",
    run: "edit Admin",
},
{
    isActive: ["manual"],
    trigger: ".o_field_widget[name='user_ids']",
    content: _t("Assign a responsible to your task"),
    tooltipPosition: "right",
    run: "click",
},
{
    isActive: ["desktop", "auto"],
    trigger: "a.dropdown-item[id*='user_ids'] span",
    content: _t("Select an assignee from the menu"),
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: "div.o_kanban_renderer > article.o_kanban_record",
    run: "click",
}, {
    isActive: ["auto"],
    trigger: 'button[name="sub_tasks_page"]',
    content: _t('Open sub-tasks notebook section'),
    run: 'click',
}, {
    isActive: ["auto"],
    trigger: '.o_field_subtasks_one2many .o_list_renderer button[role="button"]',
    content: _t('Add a sub-task'),
    run: 'click',
}, {
    isActive: ["auto"],
    trigger: '.o_field_subtasks_one2many div[name="name"] input',
    content: markup(_t('Give the sub-task a <b>name</b>')),
    run: "edit New Sub-task",
},
{
    trigger: ".o_form_project_tasks .o_form_dirty",
},
{
    isActive: ["auto"],
    trigger: ".o_form_button_save",
    content: markup(_t("You have unsaved changes - no worries! Odoo will automatically save it as you navigate.<br/> You can discard these changes from here or manually save your task.<br/>Let's save it manually.")),
    tooltipPosition: "bottom",
    run: "click",
},
{
    trigger: ".o_form_project_tasks",
},
{
    trigger: ".o_breadcrumb .o_back_button",
    content: markup(_t("Let's go back to the <b>kanban view</b> to have an overview of your next tasks.")),
    tooltipPosition: "right",
    run: 'click',
}, {
    isActive: ["auto"],
    trigger: ".o_kanban_record .o_widget_subtask_counter .subtask_list_button",
    content: _t("You can open sub-tasks from the kanban card!"),
    run: "click",
},
{
    trigger: ".o_widget_subtask_kanban_list .subtask_list",
},
{
    isActive: ["auto"],
    trigger: ".o_kanban_record .o_widget_subtask_kanban_list .subtask_create",
    content: _t("Create a new sub-task"),
    run: "click",
},
{
    trigger: ".subtask_create_input",
},
{
    isActive: ["auto"],
    trigger: ".o_kanban_record .o_widget_subtask_kanban_list .subtask_create_input input",
    content: markup(_t("Give the sub-task a <b>name</b>")),
    run: "edit Newer Sub-task && click body",
}, {
    isActive: ["auto"],
    trigger: ".o_kanban_record .o_widget_subtask_kanban_list .subtask_list_row:contains(newer sub-task) .o_field_project_task_state_selection button",
    content: _t("You can change the sub-task state here!"),
    run: "click",
},
{
    trigger: ".project_task_state_selection_menu.dropdown-menu",
},
{
    isActive: ["auto"],
    trigger: ".project_task_state_selection_menu.dropdown-menu span.text-danger",
    content: markup(_t("Mark the task as <b>Cancelled</b>")),
    run: "click",
}, {
    trigger: ".o-overlay-container:not(:visible):not(:has(.project_task_state_selection_menu))",
}, {
    isActive: ["auto"],
    trigger: ".o_kanban_record .o_widget_subtask_counter .subtask_list_button:contains('1/2')",
    content: _t("Close the sub-tasks list"),
    run: "click",
}, {
    isActive: ["auto"],
    trigger: '.o_kanban_renderer',
    // last step to confirm we've come back before considering the tour successful
    run: "click",
}]});
