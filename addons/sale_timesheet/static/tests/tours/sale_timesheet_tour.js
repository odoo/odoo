odoo.define('sale_timesheet.tour', function (require) {
"use strict";

const {Markup} = require('web.utils');
const tour = require('web_tour.tour');

tour.register('sale_timesheet_tour', {
    test: true,
    url: '/web',
}, [...tour.stepUtils.goToAppSteps("sale.sale_menu_root", 'Go to the Sales App'),
{
    trigger: 'button.o_list_button_add',
    content: 'Click on CREATE button to create a quotation with service products.',
    run: 'click',
}, {
    trigger: 'div[name="partner_id"]',
    content: 'Add the customer for this quotation (e.g. Brandon Freeman)',
    run: function (actions) {
        actions.text('Brandon Freeman', this.$anchor.find('input'));
    },
}, {
    trigger: 'ul.o_partner_autocomplete_dropdown > li:first-child > a:contains(Freeman)',
    content: 'Select the first item on the autocomplete dropdown',
    run: 'click',
},
{
    trigger: 'td.o_field_x2many_list_row_add > a:first-child',
    content: 'Click on "Add a product" to add a new product. We will add a service product.',
    run: 'click',
}, {
    trigger: '.o_field_widget[name="product_id"], .o_field_widget[name="product_template_id"]',
    content: Markup('Select a prepaid service product <i>(e.g. Service Product (Prepaid Hours))</i>'),
    run: function (actions) {
        actions.text('Service Product (Prepaid Hours)', this.$anchor.find('input'));
    },
}, {
    trigger: 'ul.ui-menu.ui-widget.ui-autocomplete > li:first-child > a:contains(Service Product (Prepaid Hours))',
    content: 'Select the prepaid service product in the autocomplete dropdown',
    run: 'click',
}, {
    trigger: 'input[name="product_uom_qty"]',
    content: "Add 10 hours as ordered quantity for this product.",
    run: 'text 10',
}, {
    trigger: 'button[name="action_confirm"]',
    content: 'Click on Confirm button to create a sale order with this quotation.',
    run: 'click',
}, {
    trigger: 'button.o_form_button_save',
    extra_trigger: '.o_form_view:not(:has(button[name="action_confirm"]:not(.o_invisible_modifier)))',
    content: 'Click on Save button to save the Sales Order.',
    run: 'click',
}, {
    trigger: '.o_form_readonly',
    content: 'Save is done and form is reloaded.',
    run: 'click',
}, tour.stepUtils.toggleHomeMenu(),
...tour.stepUtils.goToAppSteps("project.menu_main_pm", 'Go to the Project app.'),
{
    trigger: 'button.o-kanban-button-new',
    content: 'Add a new project.',
    run: 'click',
}, {
    trigger: 'input.o_field_widget.o_project_name',
    content: 'Select your project name (e.g. Project for Freeman)',
    run: function (actions) {
        actions.text('Project for Freeman', this.$anchor);
    },
}, {
    trigger: 'button[name="action_view_tasks"]',
    content: 'Click on Create button to create and enter to this newest project.',
    run: 'click',
}, {
    trigger: 'div.o_kanban_header > div:first-child',
    content: 'Select a name of your kanban column (e.g. To Do)',
    run: function (actions) {
        actions.text('To Do', this.$anchor.find('input'));
    },
}, {
    trigger: 'button.o_kanban_add',
    content: 'Click on Add button to create the column.',
    run: 'click',
}, {
    trigger: 'button.o-kanban-button-new',
    content: 'Click on Create button to create a task into your project.',
    run: 'click',
}, {
    trigger: 'input[name="name"]',
    content: 'Select the name of the task (e.g. Onboarding)',
    run: function (actions) {
        actions.text('Onboarding', this.$anchor);
    }
}, {
    trigger: 'button.o_kanban_edit',
    content: 'Click on Edit button to enter to the form view of the task.',
    position: 'bottom',
    run: 'click',
}, {
    trigger: 'div[name="partner_id"]',
    content: Markup('Select the customer of your Sales Order <i>(e.g. Brandon Freeman)</i>. Since we have a Sales Order for this customer with a prepaid service product which the remaining hours to deliver is greater than 0, the Sales Order Item in the task should be contain the Sales Order Item containing this prepaid service product.'),
    run: function (actions) {
        actions.text('Brandon Freeman', this.$anchor.find('input'));
    },
}, {
    trigger: 'ul.o_partner_autocomplete_dropdown > li:first-child > a:contains(Freeman)',
    content: 'Select the customer in the autocomplete dropdown.',
    run: 'click',
}, {
    trigger: 'div.o_notebook_headers',
    content: 'Click on Timesheets page to log a timesheet',
    run: function (actions) {
        const notebookId = $('div[name="timesheet_ids"]').closest("div.tab-pane").attr('id');
        actions.click(this.$anchor.find(`a[data-toggle="tab"][href="#${notebookId}"]`));
    },
}, {
    trigger: 'div[name="timesheet_ids"] td.o_field_x2many_list_row_add a[role="button"]',
    content: 'Click on Add a line to create a new timesheet into the task.',
    run: 'click',
}, {
    trigger: 'input[name="unit_amount"]',
    content: 'Enter one hour for this timesheet',
    run: function (actions) {
        actions.text('1', this.$anchor);
    },
}, {
    trigger: 'i.o_optional_columns_dropdown_toggle',
    content: 'The so_line field should be hidden by default. We check if it is the case by adding this field in the timesheet list view',
    run: 'click',
}, {
    trigger: 'input[name="so_line"]',
    content: 'Check the so_line field to display the column on the list view.',
    run: function (actions) {
        if (!this.$anchor.prop('checked')) {
            actions.click(this.$anchor);
        }
    },
}, {
    trigger: 'button[name="action_view_so"]',
    content: 'Click on this stat button to see the SO linked to the SOL of the task.',
    run: 'click',
}, {
    trigger: 'div[name="order_line"]',
    content: 'Check if the quantity delivered is equal to 1 hour.',
    run: function () {
        const $header = this.$anchor.find('thead > tr');
        if (!$header || $header.length === 0)
            console.error('No Sales Order Item is found in the Sales Order.');
        const tr = $header[0];
        let index = -1;
        for (let i = 0; i < tr.children.length; i++) {
            const th = tr.children.item(i);
            if (th.dataset && th.dataset.name === 'qty_delivered')
                index = i;
        }
        const qtyDelivered = this.$anchor.find(`tbody > tr:first-child > td.o_data_cell:eq(${index})`).text();
        if (qtyDelivered !== "1.00")
            console.error('The quantity delivered on this Sales Order Item should be equal to 1.00 hour. qtyDelivered = ' + qtyDelivered);
    },
}, {
    trigger: 'button[data-menu-xmlid="project.menu_project_config"]',
    content: 'Click on the Configuration menu.',
    run: 'click',
}, {
    trigger: '.dropdown-item[data-menu-xmlid="project.menu_projects_config"]',
    content: 'Select Configuration > Projects.',
    run: 'click',
}, {
    trigger: 'button.o_list_button_add',
    content: 'Click on Create button to create a new project and see the different configuration available for the project.',
    run: 'click',
}, {
    trigger: 'div.o_notebook_headers',
    content: 'Click on Settings page to check the allow_billable checkbox',
    run: function (actions) {
        const notebookId = $('div[name="allow_billable"]').closest("div.tab-pane").attr('id');
        actions.click(this.$anchor.find(`a[data-toggle="tab"][href="#${notebookId}"]`));
    },
}, {
    trigger: 'div[name="allow_billable"] > input',
    content: 'Check the allow_billable',
    run: function (actions) {
        if (!this.$anchor.prop('checked')) {
            actions.click(this.$anchor);
        }
    }
}, {
    trigger: 'div[name="partner_id"]',
    content: Markup('Add the customer for this project to select an SO and SOL for this customer <i>(e.g. Brandon Freeman)</i>.'),
    run: function (actions) {
        actions.text('Azure Interior, Brandon Freeman', this.$anchor.find('input'));
    },
}, {
    trigger: 'ul.o_partner_autocomplete_dropdown > li:first-child > a:contains(Freeman)',
    content: 'Select the customer in the autocomplete dropdown',
    run: 'click',
}, {
    trigger: 'div.o_notebook_headers',
    content: 'Click on Invoicing tab to configure the invoicing of this project.',
    run: function (actions) {
        const notebookId = $('div[name="sale_line_id"]').closest("div.tab-pane").attr('id');
        actions.click(this.$anchor.find(`a[data-toggle="tab"][href="#${notebookId}"]`));
    },
}, {
    trigger: 'div[name="sale_line_id"]',
    content: 'Select a Sales Order Item as Default Sales Order Item for each task in this project.',
    run: function (actions) {
        actions.text('S', this.$anchor.find('input'));
    },
}, {
    trigger: 'ul.ui-autocomplete > li:first-child > a',
    content: 'Select the Sales Order Item in the autocomplete dropdown.',
    run: 'click',
}, {
    trigger: 'div[name="sale_line_employee_ids"] td.o_field_x2many_list_row_add > a[role="button"]',
    content: 'Click on Add a line on the mapping list view.',
    run: 'click',
}, {
    trigger: 'div[name="sale_line_employee_ids"] div[name="employee_id"] input',
    content: 'Select an employee to link a Sales Order Item on his timesheets into this project.',
    run: 'click',
}, {
    trigger: 'ul.ui-autocomplete > li:first-child > a',
    content: 'Select the first employee in the autocomplete dropdown',
    run: 'click',
}, {
    trigger: 'div[name="sale_line_employee_ids"] div[name="sale_line_id"]',
    content: 'Select the Sales Order Item to link to the timesheets of this employee.',
    position: 'bottom',
    run: function (actions) {
        actions.text('S', this.$anchor.find('input'));
    },
}, {
    trigger: 'ul.ui-autocomplete > li:first-child > a',
    content: 'Select the first Sales Order Item in the autocomplete dropdown.',
    run: 'click',
}, {
    trigger: 'input[name="name"]',
    content: 'Set Project name',
    run: function (actions) {
        actions.text('Project with employee mapping', this.$anchor);
    },
}, {
    trigger: '.o_form_button_save',
    content: 'Save Project',
}, {
    trigger: '.dropdown-item[data-menu-xmlid="project.menu_projects"]',
    content: 'Select Projects',
}, {
    // an invisible element cannot be used as a trigger so this small hack is mandatory for the next step
    trigger: 'div.o_kanban_primary_left :contains("Project for Freeman")',
    content: 'Open the project dropdown',
    run: function () {
        $('.o_kanban_record:contains("Project for Freeman") .o_dropdown_kanban').css('visibility', 'visible');
    },
}, {
    trigger: '.oe_kanban_global_click :contains("Project for Freeman") .o_dropdown_kanban',
    content: 'Open the project dropdown',
}, {
    trigger: '.o_kanban_record:contains("Project for Freeman") .dropdown-menu a:contains("Edit")',
    content: 'Start editing the project',
}, {
    trigger: 'div.o_notebook_headers',
    content: 'Click on Invoicing tab to configure the invoicing of this project.',
    run: function (actions) {
        const notebookId = $('div[name="sale_line_id"]').closest("div.tab-pane").attr('id');
        actions.click(this.$anchor.find(`a[data-toggle="tab"][href="#${notebookId}"]`));
    },
}, {
    trigger: 'div[name="sale_line_id"]',
    content: 'Select the first sale order of the list',
    run: function (actions) {
        actions.text('Prepaid', this.$anchor.find('input'));
    },
}, {
    trigger: 'ul.ui-autocomplete > li:first-child > a',
    content: 'Select the first item on the autocomplete dropdown',
}, {
    trigger: '.o_form_button_save',
    content: 'Save the modifications',
}, {
    trigger: '.o_back_button',
    content: 'Go back to the kanban view the project created',
}, {
    trigger: '.oe_kanban_global_click :contains("Project for Freeman")',
    content: 'Open the project',
}, {
    trigger: ".o_project_updates_breadcrumb",
    content: 'Open Updates',
}, {
    trigger: ".o_rightpanel_title:eq(0):contains('Sales')",
    content: 'Check the user sees Sales section',
    run: function () {},
}, {
    trigger: ".o_rightpanel_data:eq(0):contains('Prepaid Hours')",
    content: 'Check the user sees a line in the Sales section',
    run: function () {},
}, {
    trigger: ".oe_button_box .o_stat_text:contains('Sales Orders')",
    content: 'Check the user sees Sales Orders Stat Button',
    run: function () {},
}, {
    trigger: ".o_rightpanel_title:eq(1):contains('Profitability')",
    content: 'Check the user sees Profitability section',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section:eq(2) .o_rightpanel_data > .o_rightpanel_subsection:eq(0) > table > thead > tr > th:eq(0):contains('Revenues')",
    content: 'Check the user sees Profitability subsection row',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section:eq(2) .o_rightpanel_data > .o_rightpanel_subsection:eq(1) > table > thead > tr > th:eq(0):contains('Costs')",
    content: 'Check the user sees Profitability subsection row',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section:eq(2) .o_rightpanel_data > .o_rightpanel_subsection:eq(2) > table > thead > tr > th:eq(0):contains('Margin')",
    content: 'Check the user sees Profitability subsection row',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section .o_rightpanel_title:contains('Milestones')",
    content: 'Check the user sees Milestones section',
}, {
    trigger: ".o_add_milestone a",
    content: "Add a first milestone",
}, {
    trigger: "input.o_field_widget[name=name]",
    content: "Edit new Milestone",
    run: 'text New milestone',
}, {
    trigger: "input.datetimepicker-input[name=deadline]",
    content: "Edit new Milestone",
    run: 'text 12/12/2099',
}, {
    trigger: ".modal-footer button",
    content: "Save new Milestone",
}, {
    trigger: ".o-kanban-button-new",
    content: "Create new Project Update",
}, {
    trigger: "input.o_field_widget[name=name]",
    content: "Give a name to Project Update",
    run: 'text New update',
}, {
    trigger: ".o_form_button_save",
    content: "Save Project Update",
}, {
    trigger: ".o_field_widget[name=description] h3:contains('Sold')",
    content: "Sold title must be in description in description",
    run: function () {},
    }, {
    trigger: ".o_field_widget[name=description] td:contains('Prepaid Hours')",
    content: "Prepaid Hours title must be in description",
    run: function () {},
}, {
    trigger: ".o_field_widget[name=description] h3:contains('Profitability')",
    content: "Profitability title must be in description",
    run: function () {},
}, {
    trigger: ".o_field_widget[name=description] h3:contains('Milestones')",
    content: "Milestones title must be in description",
    run: function () {},
},
// This step is currently needed in order to prevent a session timeout at the end of the test.
tour.stepUtils.toggleHomeMenu(),
...tour.stepUtils.goToAppSteps("project.menu_main_pm", 'Go to the Project app.'),
]);
});
