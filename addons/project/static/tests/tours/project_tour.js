/** @odoo-module */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('project_test_tour', {
    test: true,
    url: '/web',
    steps: () => [
    stepUtils.showAppsMenuItem(), {
        trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    }, {
        trigger: '.o-kanban-button-new',
        extra_trigger: '.o_project_kanban',
        width: 200,
    }, {
        trigger: '.o_project_name input',
        run: 'edit New Project',
        id: 'project_creation',
    }, {
        trigger: '.o_open_tasks',
        run: "click .modal:visible .btn.btn-primary",
    }, {
        trigger: ".o_kanban_project_tasks .o_column_quick_create .input-group input",
        run: "edit New",
    }, {
        trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
        auto: true,
    }, {
        trigger: ".o_kanban_project_tasks .o_column_quick_create .input-group input",
        extra_trigger: '.o_kanban_group',
        run: "edit Done",
    }, {
        trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
        auto: true,
    }, {
        trigger: '.o-kanban-button-new',
        extra_trigger: '.o_kanban_group:eq(0)'
    }, {
        trigger: '.o_kanban_quick_create div.o_field_char[name=display_name] input',
        extra_trigger: '.o_kanban_project_tasks',
        run: "edit New task",
    }, {
        trigger: '.o_kanban_quick_create .o_kanban_add',
    }, {
        trigger: '.o_kanban_record span:contains("New task")',
    }, {
        trigger: 'a[name="sub_tasks_page"]',
        content: 'Open sub-tasks notebook section',
        run: 'click',
    }, {
        trigger: '.o_field_subtasks_one2many .o_list_renderer a[role="button"]',
        content: 'Add a subtask',
        run: 'click',
    }, {
        trigger: '.o_field_subtasks_one2many div[name="name"] input',
        content: 'Set subtask name',
        run: "edit new subtask",
    }, {
        trigger: ".o_breadcrumb .o_back_button",
        content: 'Go back to kanban view',
        position: "right",
    }, {
        trigger: ".o_kanban_record .oe_kanban_content .o_widget_subtask_counter .subtask_list_button",
        content: 'open sub-tasks from kanban card',
    }, {
        trigger: ".o_kanban_record .o_widget_subtask_kanban_list .subtask_create",
        extra_trigger: ".o_widget_subtask_kanban_list .subtask_list",
        content: 'Create a new sub-task',
    }, {
        trigger: ".o_kanban_record .o_widget_subtask_kanban_list .subtask_create_input input",
        extra_trigger: ".subtask_create_input",
        content: 'Give the sub-task a name',
        run: "edit newer subtask && click(div.subtask_create_input button:contains(SAVE))",
    }, {
        trigger: ".o_kanban_record .o_widget_subtask_kanban_list .subtask_list_row:first-child .o_field_project_task_state_selection button",
        content: 'Change the subtask state',
    }, {
        trigger: ".dropdown-menu span.text-danger",
        extra_trigger: ".dropdown-menu",
        content: 'Mark the task as Canceled',
    }, {
        trigger: ".o_kanban_record .oe_kanban_content .o_widget_subtask_counter .subtask_list_button:contains('1/2')",
        content: 'Close the sub-tasks list',
        id: "quick_create_tasks",
    }, {
        trigger: '.o_field_text[name="name"] textarea',
        content: 'Set task name',
        run: "edit New task",
    }, {
        trigger: 'div[name="user_ids"].o_field_many2many_tags_avatar input',
        content: 'Assign the task to you',
        run: 'click',
    }, {
        trigger: 'ul.ui-autocomplete a .o_avatar_many2x_autocomplete',
        content: 'Assign the task to you',
    }, {
        trigger: 'a[name="sub_tasks_page"]',
        content: 'Open sub-tasks notebook section',
        run: 'click',
    }, {
        trigger: '.o_field_subtasks_one2many .o_list_renderer a[role="button"]',
        content: 'Add a subtask',
        run: 'click',
    }, {
        trigger: '.o_field_subtasks_one2many div[name="name"] input',
        content: 'Set subtask name',
        run: "edit new subtask",
    }, {
        trigger: 'button[special="save"]',
        extra_trigger: '.o_field_many2many_tags_avatar .o_m2m_avatar',
        content: 'Save task',
    },
]});
