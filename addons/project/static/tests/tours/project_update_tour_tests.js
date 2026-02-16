import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('project_update_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    run: "click",
},
{
    trigger: ".o_project_kanban",
},
{
    trigger: '.o-kanban-button-new',
    run: "click",
}, {
    isActive: ['.o-kanban-button-new.dropdown'], // if the project template dropdown is active
    trigger: 'button.o-dropdown-item:contains("New Project")',
    run: "click",
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
    isActive: ["auto"],
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    run: "click",
},
{
    trigger: ".o_kanban_group",
},
{
    trigger: ".o_kanban_project_tasks .o_column_quick_create .input-group input",
    run: "edit Done",
}, {
    isActive: ["auto"],
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    run: "click",
},
{
    trigger: ".o_kanban_group:eq(0)",
},
{
    trigger: '.o-kanban-button-new',
    run: "click",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: '.o_kanban_quick_create div.o_field_char[name=display_name] input',
    run: "edit New task",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: '.o_kanban_quick_create .o_kanban_add',
    run: "click",
},
{
    trigger: ".o_kanban_group:eq(0)",
},
{
    trigger: '.o-kanban-button-new',
    run: "click",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: '.o_kanban_quick_create div.o_field_char[name=display_name] input',
    run: "edit Second task",
},
{
    trigger: ".o_kanban_project_tasks",
},
{
    trigger: '.o_kanban_quick_create .o_kanban_add',
    run: "click",
}, {
    trigger: ".o_kanban_group:nth-child(2) .o_kanban_header",
    run: "hover && click .o_kanban_group:nth-child(2) .o_kanban_header .dropdown-toggle",
}, {
    trigger: ".dropdown-item.o_group_edit",
    run: "click",
}, {
    trigger: ".modal .o_field_widget[name=fold] input",
    run: "click",
}, {
    trigger: ".modal .modal-footer button",
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
{
    trigger: '.o_kanban_project_tasks',
},
{
    trigger: ".o_kanban_record",
    run: "drag_and_drop(.o_kanban_group:eq(1))",
}, {
    trigger: ".breadcrumb-item.o_back_button",
    run: "click",
}, {
    trigger: ".o_kanban_record:contains('New Project')",
}, {
    trigger: ".o_switch_view.o_list",
    run: "click",
}, {
    trigger: "tr.o_data_row td[name='name']:contains('New Project')",
    run: "click",
}, {
    trigger: ".nav-link:contains('Settings')",
    run: "click",
}, {
    trigger: "div[name='allow_milestones'] input",
    run: "click",
}, {
    trigger: ".o_form_button_save",
    run: "click",
}, {
    trigger: "button[name='action_view_tasks']",
    run: "click",
}, {
    trigger: ".o_control_panel_navigation button i.fa-sliders",
    content: 'Open embedded actions',
    run: "click",
}, {
    trigger: "span.o-dropdown-item:contains('Top Menu')",
    run: "click",
}, {
    trigger: ".o-dropdown-item div span:contains('Updates')",
    content: "Put Updates in the embedded actions",
    run: "click",
}, {
    trigger: ".o_embedded_actions button span:contains('Updates')",
    content: "Open Updates",
    run: "click",
}, {
    trigger: ".o_list_button_add",
    content: "Create a new update",
    run: "click",
}, {
    trigger: "div.o_field_widget[name=name] input",
    run: "edit New update",
}, {
    trigger: ".o_form_button_save",
    run: "click",
}, {
    trigger: '.o_back_button',
    content: 'Go back to the kanban view the project',
    run: "click",
}, {
    trigger: '.o_switch_view.o_kanban',
    content: 'Open Kanban View of Updates',
    run: "click",
},
{
    trigger: '.o_kanban_view',
},
{
    trigger: '.o_back_button',
    content: 'Go back to the list view the project',
    run: "click",
},
]});
