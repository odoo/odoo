/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('project_update_tour', {
    test: true,
    url: '/web',
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_project_kanban',
    width: 200,
}, {
    trigger: '.o_project_name input',
    run: "edit New Project",
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
    extra_trigger: '.o_kanban_project_tasks'
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_group:eq(0)'
}, {
    trigger: '.o_kanban_quick_create div.o_field_char[name=display_name] input',
    extra_trigger: '.o_kanban_project_tasks',
    run: "edit Second task",
}, {
    trigger: '.o_kanban_quick_create .o_kanban_add',
    extra_trigger: '.o_kanban_project_tasks'
}, {
    trigger: '.o_kanban_group:nth-child(2) .o_kanban_header .o_kanban_config .dropdown-toggle',
}, {
    trigger: ".dropdown-item.o_column_edit",
}, {
    trigger: ".o_field_widget[name=fold] input",
}, {
    trigger: ".modal-footer button",
}, {
    trigger: ".o_kanban_record .oe_kanban_content",
    extra_trigger: '.o_kanban_project_tasks',
    run: "drag_and_drop(.o_kanban_group:eq(1))",
}, {
    trigger: ".o_control_panel_navigation button i.fa-sliders",
    content: 'Open embedded actions'
}, {
    trigger: ".o_embedded_actions_buttons_wrapper button i.fa-sliders",
    content: "Open embedded actions dropdown"
}, {
    trigger: ".o-dropdown-item div span:contains('Project Updates')",
    content: "Put Project Updates in the embedded actions"
}, {
    trigger: ".o_embedded_actions_buttons_wrapper button span:contains('Project Updates')",
    content: "Open Project Updates"
}, {
    trigger: ".o_add_milestone a",
    content: "Add a first milestone"
}, {
    trigger: "div.o_field_widget[name=name] input",
    run: "edit New milestone",
}, {
    trigger: "input[data-field=deadline]",
    run: "edit 12/12/2099 && click body",
}, {
    trigger: ".modal-footer .o_form_button_save"
}, {
    trigger: ".o_add_milestone a",
}, {
    trigger: "div.o_field_widget[name=name] input",
    run: "edit Second milestone",
}, {
    trigger: "input[data-field=deadline]",
    run: "edit 12/12/2022 && click body",
}, {
    trigger: ".modal-footer .o_form_button_save"
}, {
    trigger: ".o_rightpanel_milestone:eq(1) .o_milestone_detail",
}, {
    trigger: "input[data-field=deadline]",
    run: "edit 12/12/2100 && click body",
}, {
    trigger: ".modal-footer .o_form_button_save"
}, {
    trigger: ".o-kanban-button-new",
    content: "Create a new update"
}, {
    trigger: "div.o_field_widget[name=name] input",
    run: "edit New update",
}, {
    trigger: ".o_form_button_save"
}, {
    trigger: ".o_field_widget[name='description'] h1:contains('Activities')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name='description'] h3:contains('Milestones')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name='description'] div[name='milestone'] ul li:contains('(12/12/2099 => 12/12/2100)')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name='description'] div[name='milestone'] ul li:contains('(due 12/12/2022)')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name='description'] div[name='milestone'] ul li:contains('(due 12/12/2100)')",
    run: function () {},
}, {
    trigger: '.o_back_button',
    content: 'Go back to the kanban view the project',
}, {
    trigger: '.o_switch_view.o_list',
    content: 'Open List View of Project Updates',
}, {
    trigger: '.o_back_button',
    content: 'Go back to the kanban view the project',
    extra_trigger: '.o_list_view',
},
]});
