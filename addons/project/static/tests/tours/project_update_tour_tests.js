/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('project_update_tour', {
    test: true,
    url: '/web',
},
[tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_project_kanban',
    width: 200,
}, {
    trigger: 'input.o_project_name',
    run: 'text New Project'
}, {
    trigger: '.o_open_tasks',
    run: function (actions) {
        actions.auto('.modal:visible .btn.btn-primary');
    },
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .input-group",
    run: function (actions) {
        actions.text("New", this.$anchor.find("input"));
    },
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    auto: true,
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .input-group",
    extra_trigger: '.o_kanban_group',
    run: function (actions) {
        actions.text("Done", this.$anchor.find("input"));
    },
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    auto: true,
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_group:eq(0)'
}, {
    trigger: '.o_kanban_quick_create input.o_field_char[name=name]',
    extra_trigger: '.o_kanban_project_tasks',
    run: 'text New task'
}, {
    trigger: '.o_kanban_quick_create .o_kanban_add',
    extra_trigger: '.o_kanban_project_tasks'
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_group:eq(0)'
}, {
    trigger: '.o_kanban_quick_create input.o_field_char[name=name]',
    extra_trigger: '.o_kanban_project_tasks',
    run: 'text Second task'
}, {
    trigger: '.o_kanban_quick_create .o_kanban_add',
    extra_trigger: '.o_kanban_project_tasks'
}, {
    trigger: '.o_kanban_header:eq(1)',
    run: function () {
        $('.o_kanban_config.dropdown .dropdown-toggle').eq(1).click();
    }
}, {
    trigger: ".dropdown-item.o_column_edit",
}, {
    trigger: ".o_field_widget[name=fold] input",
}, {
    trigger: ".modal-footer button",
}, {
    trigger: ".o_kanban_record .oe_kanban_content",
    extra_trigger: '.o_kanban_project_tasks',
    run: "drag_and_drop .o_kanban_group:eq(1) ",
}, {
    trigger: ".o_project_updates_breadcrumb",
}, {
    trigger: ".o_add_milestone a",
}, {
    trigger: "input.o_field_widget[name=name]",
    run: 'text New milestone'
}, {
    trigger: "input.datetimepicker-input[name=deadline]",
    run: 'text 12/12/2099'
}, {
    trigger: ".modal-footer button"
}, {
    trigger: ".o_add_milestone a",
}, {
    trigger: "input.o_field_widget[name=name]",
    run: 'text Second milestone'
}, {
    trigger: "input.datetimepicker-input[name=deadline]",
    run: 'text 12/12/2021'
}, {
    trigger: ".modal-footer button"
}, {
    trigger: ".o_rightpanel_left_button:eq(0)"
}, {
    trigger: ".breadcrumb :contains('Tasks Analysis')",
}, {
    trigger: ".o_back_button"
}, {
    trigger: ".o_rightpanel_left_button:eq(1)"
}, {
    trigger: ".breadcrumb :contains('Burndown Chart')",
}, {
    trigger: ".o_back_button"
}, {
    trigger: ".o_open_milestone:eq(1) .o_milestone_detail span:eq(0)",
    extra_trigger: ".o_add_milestone a",
    run: function () {
        setTimeout(() => {
            this.$anchor.click();
        }, 500);
    },
}, {
    trigger: "input.datetimepicker-input[name=deadline]",
    run: 'text 12/12/2100'
}, {
    trigger: ".modal-footer button"
}, {
    trigger: ".o-kanban-button-new"
}, {
    trigger: "input.o_field_widget[name=name]",
    run: 'text New update'
}, {
    trigger: ".o_form_button_save"
}, {
    trigger: ".o_field_widget[name=description] :contains('1 tasks are open, out of 2.')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name=description] :contains('2 were created')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name=description] :contains('1 was closed')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name=description] :contains('New milestone') :contains('(due on 12/12/2100)')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name=description] :contains('New milestone') :contains('(12/12/2099 => 12/12/2100)')",
    run: function () {},
}]);
