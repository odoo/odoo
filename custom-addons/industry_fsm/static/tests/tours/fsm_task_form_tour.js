/** @odoo-module */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add(
    "fsm_task_form_tour",
    {
        url: '/web',
        test: true,
        steps: () => [
            ...stepUtils.goToAppSteps("industry_fsm.fsm_menu_root", "Open app Field Service"),
            {
                content: "Create a new task",
                trigger: '.o-kanban-button-new',
            }, {
                content: "Create a new task from form view in fsm",
                trigger: 'div[name="name"] textarea.o_input',
                run: 'text New fsm parent task',
            }, {
                content: "Go to subtask tab of the notebook",
                trigger: 'a[name="sub_tasks_page"]',
                run: 'click',
            }, {
                content: 'Add a subtask',
                trigger: '.o_field_subtasks_one2many .o_list_renderer a[role="button"]',
                run: 'click',
            }, {
                content: 'Set subtask name',
                trigger: '.o_field_subtasks_one2many div[name="name"] input',
                run: 'text New fsm child task',
            }, {
                content: 'Add a customer to the parent task',
                trigger: 'div[name="partner_id"] input.o_input',
                run: 'text Azure Interior',
            }, {
                content: 'Validate Customer',
                trigger: '.ui-menu-item a:contains("Azure Interior")',
            }, {
                content: 'Open Menu All Tasks',
                trigger: 'button.dropdown-toggle[data-menu-xmlid="industry_fsm.fsm_menu_all_tasks_root"]',
                run: 'click',
            }, {
                content: 'Go to All Tasks list view',
                trigger: 'a[data-menu-xmlid="industry_fsm.fsm_menu_all_tasks_todo"]',
                run: 'click',
            }, {
                content: 'Switch to kanban view',
                trigger: 'button.o_switch_view.o_kanban',
                run: 'click',
            }, {
                content: "Check that parent task exists",
                trigger: '.o_kanban_record_title span:contains("New fsm parent task")',
            }
        ]
    }
);
