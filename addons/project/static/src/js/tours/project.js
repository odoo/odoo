/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('project_tour', {
    sequence: 110,
    url: "/web",
    rainbowManMessage: _t("Congratulations, you are now a master of project management."),
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    content: markup(_t('Want a better way to <b>manage your projects</b>? <i>It starts here.</i>')),
    position: 'right',
    edition: 'community',
}, {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    content: markup(_t('Want a better way to <b>manage your projects</b>? <i>It starts here.</i>')),
    position: 'bottom',
    edition: 'enterprise',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_project_kanban',
    content: markup(_t('Let\'s create your first <b>project</b>.')),
    position: 'bottom',
    width: 200,
}, {
    trigger: '.o_project_name input',
    content: markup(_t('Choose a <b>name</b> for your project. <i>It can be anything you want: the name of a customer, of a product, of a team, of a construction site, etc.</i>')),
    position: 'right',
}, {
    trigger: '.o_open_tasks',
    content: markup(_t('Let\'s create your first <b>project</b>.')),
    position: 'top',
    run: function (actions) {
        actions.auto('.modal:visible .btn.btn-primary');
    },
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_header input",
    content: markup(_t("Add columns to organize your tasks into <b>stages</b> <i>e.g. New - In Progress - Done</i>.")),
    position: 'bottom',
    run: "text Test Stage",
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    content: markup(_t('Let\'s create your first <b>stage</b>.')),
    position: 'right',
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_header input",
    extra_trigger: '.o_kanban_group',
    content: markup(_t("Add columns to organize your tasks into <b>stages</b> <i>e.g. New - In Progress - Done</i>.")),
    position: 'bottom',
    run: "text Second Test Stage",
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    content: markup(_t('Let\'s create your second <b>stage</b>.')),
    position: 'right',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_group:eq(1)',
    content: markup(_t("Let's create your first <b>task</b>.")),
    position: 'bottom',
    width: 200,
}, {
    trigger: '.o_kanban_quick_create div.o_field_char[name=display_name] input',
    extra_trigger: '.o_kanban_project_tasks',
    content: markup(_t('Choose a task <b>name</b> <i>(e.g. Website Design, Purchase Goods...).</i>')),
    position: 'right',
    run: "text Test Task",
}, {
    trigger: '.o_kanban_quick_create .o_kanban_add',
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("Add your task once it is ready."),
    position: "bottom",
}, {
    trigger: '.o_kanban_record .o_field_project_task_state_selection button',
    content: markup(_t("You can change the <b>state</b> of the task here.")),
    position: "bottom",
}, {
    trigger: '.o_kanban_record .o_field_project_task_state_selection .dropdown-menu .dropdown-item:has(.o_status_green)',
    extra_trigger: '.o_kanban_record .o_field_project_task_state_selection .dropdown-menu',
    content: markup(_t("The <b>state</b> of a task indicates to you and your collegues if the task is ready for the next stage, needs some changes, ... Here, just mark the task as <i>Approved</i> for the moment.")),
    position: "right",
}, {
    trigger: '.o-kanban-button-new',
    content: markup(_t("Create a second <b>task</b>.")),
    position: 'bottom',
}, {
    trigger: '.o_kanban_quick_create div.o_field_char[name=display_name] input',
    extra_trigger: '.o_kanban_project_tasks',
    content: markup(_t('Choose a task <b>name</b> <i>(e.g. Website Design, Purchase Goods...).</i>')),
    position: 'right',
    run: "text Second Test Task",
}, {
    trigger: '.o_kanban_quick_create .o_kanban_add',
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("Add your task once it is ready."),
    position: "bottom",
}, {
    trigger: '.o_kanban_group:first-child .o_kanban_header .o_column_progress .bg-success',
    content: markup(_t("You can click on the progress bar to display only the tasks with the same <b>state</b>.")),
    position: "top",
}, {
    trigger: '.o_kanban_group:first-child .o_kanban_header .o_column_progress .bg-success',
    content: _t("Click again to remove the filter."),
    position: "top",
}, {
    trigger: ".o_kanban_record:has(.o_field_project_task_state_selection .dropdown-toggle .o_status_green) .oe_kanban_content",
    extra_trigger: '.o_kanban_project_tasks',
    content: markup(_t("<b>Drag &amp; drop</b> the card to change your task from stage.")),
    position: "bottom",
    mobile: false,
    run: "drag_and_drop_native .o_kanban_group:eq(1) ",
}, {
    trigger: ".o_kanban_group:eq(1) .o_kanban_record .o_field_project_task_state_selection button",
    extra_trigger: '.o_kanban_project_tasks',
    content: markup(_t("Notice that the task <b>state</b> goes back to <i>In Progress</i> when the task changes state.")),
    position: "bottom",
    mobile: false,
    run: () => {},
}, {
    trigger: ".o_kanban_record:nth-of-type(2)",
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("Let's start working on your task."),
    position: "bottom",
}, {
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-sendMessage",
    extra_trigger: '.o_form_project_tasks',
    content: markup(_t("Use the chatter to <b>send emails</b> and communicate efficiently with your customers. Add new people to the followers' list to make them aware of the main changes about this task.")),
    width: 350,
    position: "bottom",
}, {
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-logNote",
    extra_trigger: '.o_form_project_tasks',
    content: markup(_t("<b>Log notes</b> for internal communications <i>(the people following this task won't be notified of the note you are logging unless you specifically tag them)</i>. Use @ <b>mentions</b> to ping a colleague or # <b>mentions</b> to reach an entire team.")),
    width: 350,
    position: "bottom"
}, {
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-activity",
    extra_trigger: '.o_form_project_tasks',
    content: markup(_t("Create <b>activities</b> to set yourself to-dos or to schedule meetings.")),
    position: "bottom",
}, {
    trigger: ".modal-dialog button[name='action_schedule_activities']",
    extra_trigger: '.o_form_project_tasks',
    content: _t("Schedule your activity once it is ready."),
    position: "bottom",
    run: "click",
}, {
    trigger: ".o_field_widget[name='user_ids']",
    extra_trigger: '.o_form_project_tasks',
    content: _t("Assign a responsible to your task."),
    position: "right",
    run() {
        document.querySelector('.o_field_widget[name="user_ids"] input').click();
    }
}, {
    trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
    auto: true,
}, {
    trigger: ".o_field_project_task_state_selection .dropdown-toggle",
    content: markup(_t("You can also change the <b>state</b> of the task here.")),
    position: "bottom",
    run: "click",
}, {
    trigger: ".o_field_project_task_state_selection .dropdown-toggle",
    content: markup(_t("Click again to close the dropdown.")),
    position: "left",
    run: "click",
}, {
    trigger: 'a[name="sub_tasks_page"]',
    content: _t('Open sub-tasks notebook section.'),
    run: 'click',
}, {
    trigger: '.o_field_subtasks_one2many .o_list_renderer a[role="button"]',
    content: _t('Add a sub-task.'),
    run: 'click',
}, {
    trigger: '.o_field_subtasks_one2many div[name="name"] input',
    content: markup(_t('Give the sub-task a <b>name</b>.')),
    run: 'text New Sub-task'
}, {
    trigger: ".breadcrumb-item:not(.active):last",
    extra_trigger: '.o_form_project_tasks',
    content: markup(_t("Let's go back to the <b>kanban view</b> to have an overview of your next tasks.")),
    position: "right",
    mobile: false,
    run: 'click',
}, {
    trigger: ".o_back_button",
    extra_trigger: '.o_form_project_tasks',
    content: markup(_t("Let's go back to the <b>kanban view</b> to have an overview of your next tasks.")),
    position: "right",
    mobile: true,
    run: 'click',
}, {
    trigger: '.o_kanban_record .o_field_project_task_state_selection button',
    content: markup(_t("Check the <b>state</b> of the task here again.")),
    position: "bottom",
}, {
    trigger: '.o_kanban_record .o_field_project_task_state_selection .dropdown-menu .dropdown-item:has(.fa-times-circle)',
    content: markup(_t("You can use the last two <b>states</b> (<i>Cancelled</i> and <i>Done</i>) to <b>close</b> the task. \
    Closed task won't appear in the kanban view by default. Try to set this task as <i>Cancelled</i>.")),
    position: "right",
}, {
    trigger: '.o_kanban_record:has(.o_field_project_task_state_selection .dropdown-toggle:has(.fa-times-circle))',
    content: _t("You can see that the task was blurred but it won't disappear until you reload this page. Click on the task."),
    position: "right",
}, {
    trigger: ".breadcrumb-item:not(.active):last",
    extra_trigger: '.o_form_project_tasks',
    content: markup(_t("Go back to the <b>kanban view</b>.")),
    position: "right",
    mobile: false,
    run: 'click',
}, {
    trigger: ".o_back_button",
    extra_trigger: '.o_form_project_tasks',
    content: markup(_t("Let's go back to the <b>kanban view</b> to have an overview of your next tasks.")),
    position: "right",
    mobile: true,
    run: 'click',
}, {
    trigger: ".o_control_panel_navigation button:has(.fa-search)",
    content: _t("Open the filter search input."),
    position: "bottom",
    mobile: true,
    run: 'click',
}, {
    trigger: ".o_control_panel_actions .o_searchview_input_container .o_searchview_facet .o_facet_remove",
    content: markup(_t("Remove the default <i>Open Tasks</i> filter.")),
    position: "bottom",
    run: 'click',
}, {
    trigger: '.o_kanban_group .o_kanban_header .o_column_progress .bg-danger',
    content: _t("Once the filter is removed, your closed tasks will be visible again."),
    position: "right",
    run: () => {},
}, {
    trigger: '.o_kanban_renderer',
    // last step to confirm we've come back before considering the tour successful
    auto: true
}]});
