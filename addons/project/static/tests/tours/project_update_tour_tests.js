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
    trigger: '.o_back_button',
    content: 'Go back to edit the project created',
}, {
    // an invisible element cannot be used as a trigger so this small hack is mandatory for the next step
    trigger: '.o_kanban_record:contains("New Project")',
    run: function () {
        $('.o_kanban_record:contains("New Project") .o_dropdown_kanban').css('visibility', 'visible');
    }
}, {
    trigger: '.oe_kanban_global_click :contains("New Project") .o_dropdown_kanban',
    content: 'Open the project dropdown'
}, {
    trigger: '.o_kanban_record:contains("New Project") .dropdown-menu a:contains("See More")',
    content: 'Start editing the project',
}, {
    trigger: '.nav-item:contains("Invoicing") .nav-link',
    content: 'Start the assignement of a default sale order id to the project'
}, {
    trigger: '.o_form_button_edit',
    content: 'Start editing the project'
}, {
    trigger: 'div[name="sale_line_id"]',
    content: 'Select the first sale order of the list',
    run: function (actions) {
        actions.text('Prepaid', this.$anchor.find('input'));
    },
}, {
    trigger: 'ul.ui-autocomplete > li:first-child > a',
    content: 'Select the first item on the autocomplete dropdown'
}, {
    trigger: '.o_form_button_save',
    content: 'Save the modifications'
}, { 
    trigger: '.o_back_button',
    content: 'Go back to the kanban view the project created',
}, {
    trigger: '.oe_kanban_global_click :contains("New Project")',
    content: 'Open the project'
}, {    
    trigger: ".o_project_updates_breadcrumb",
    content: 'Open Updates'
}, {
    trigger: ".oe_button_box .o_stat_text:contains('Sales Order')",
    run: function () {}
}, {
    trigger: ".o_rightpanel_title:eq(0):contains('Sold')",
    content: 'Check the user sees Sold section',
    run: function () {}
}, {
    trigger: ".o_rightpanel_left_text:eq(0):contains('Prepaid Hours')",
    content: 'Check the user sees Sold subsection',
    run: function () {},
}, {
    trigger: ".o_rightpanel_title:eq(1):contains('Total Sold')",
    content: 'Check the user sees Total Sold section',
    run: function () {}
}, {
    trigger: ".o_rightpanel_header:eq(1) .o_rightpanel_right_col:contains('Hours')",
    content: 'Check the user sees Total Sold hours title',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section:eq(2) .o_rightpanel_data_row:contains('Effective')",
    content: 'Check the user sees Total Sold subsection row',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section:eq(2) .o_rightpanel_data_row:contains('Remaining')",
    content: 'Check the user sees Total Sold subsection row',
    run: function () {},
}, {
    trigger: ".o_rightpanel_title:eq(2):contains('Profitability')",
    content: 'Check the user sees Profitability section',
    run: function () {}
}, {
    trigger: ".o_rightpanel_section:eq(3) .o_rightpanel_data_row:contains('Revenues')",
    content: 'Check the user sees Profitability subsection row',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section:eq(3) .o_rightpanel_data_row:contains('Costs')",
    content: 'Check the user sees Profitability subsection row',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section:eq(3) .o_rightpanel_data_row:contains('Margin')",
    content: 'Check the user sees Profitability subsection row',
    run: function () {},
}, {
    trigger: ".o_add_milestone a",
    content: "Add a first milestone"
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
    run: 'text 12/12/2022'
}, {
    trigger: ".modal-footer button"
}, {
    trigger: '.o_back_button',
    content: 'Go back to edit to the list view',

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
    trigger: ".o-kanban-button-new",
    content: "Create a new update"
}, {
    trigger: "input.o_field_widget[name=name]",
    run: 'text New update'
}, {
    trigger: ".o_form_button_save"
}, {
    trigger: ".o_field_widget[name=description] h1:contains('Activities')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name=description] h3:contains('Sold')",
    run: function () {},
    }, {
    trigger: ".o_field_widget[name=description] td:contains('Customer Care')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name=description] h3:contains('Profitability')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name=description] h3:contains('Milestones')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name=description] div[name='milestone'] ul li:contains('(12/12/2099 => 12/12/2100)')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name=description] div[name='milestone'] ul li span:contains('(due on 12/12/2022)')",
    run: function () {},
}, {
    trigger: ".o_field_widget[name=description] div[name='milestone'] ul li span:contains('(due on 12/12/2100)')",
    run: function () {},
}]);
