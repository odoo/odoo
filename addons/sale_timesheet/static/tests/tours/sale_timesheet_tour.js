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
}, {
    trigger: 'div[name="partner_id"] input',
    content: 'Add the customer for this quotation (e.g. Brandon Freeman)',
    run: 'text Brandon Freeman',
}, {
    trigger: 'div[name="partner_id"] ul > li:first-child > a:contains(Freeman)',
    content: 'Select the first item on the autocomplete dropdown',
},
{
    trigger: 'td.o_field_x2many_list_row_add > a:first-child',
    content: 'Click on "Add a product" to add a new product. We will add a service product.',
}, {
    trigger: '.o_field_html[name="product_id"], .o_field_widget[name="product_template_id"] input',
    content: Markup('Select a prepaid service product <i>(e.g. Service Product (Prepaid Hours))</i>'),
    run: 'text Service Product (Prepaid Hours)',
}, {
    trigger: 'ul.ui-autocomplete a:contains(Service Product (Prepaid Hours))',
    content: 'Select the prepaid service product in the autocomplete dropdown',
}, {
    trigger: 'div[name="product_uom_qty"] input',
    content: "Add 10 hours as ordered quantity for this product.",
    run: 'text 10',
}, {
    trigger: 'div[name="name"] textarea:propValueContains(Service Product)',
    run: () => {}
}, {
    trigger: 'button[name="action_confirm"]',
    content: 'Click on Confirm button to create a sale order with this quotation.',
}, tour.stepUtils.toggleHomeMenu(),
...tour.stepUtils.goToAppSteps("project.menu_main_pm", 'Go to the Project app.'),
{
    trigger: 'button.o-kanban-button-new',
    content: 'Add a new project.',
}, {
    trigger: '.o_field_widget.o_project_name input',
    content: 'Select your project name (e.g. Project for Freeman)',
    run: 'text Project for Freeman',
}, {
    trigger: 'button[name="action_view_tasks"]',
    content: 'Click on Create button to create and enter to this newest project.',
}, {
    trigger: 'div.o_kanban_header > div:first-child input',
    content: 'Select a name of your kanban column (e.g. To Do)',
    run: 'text To Do',
}, {
    trigger: 'button.o_kanban_add',
    content: 'Click on Add button to create the column.',
}, {
    trigger: 'button.o-kanban-button-new',
    content: 'Click on Create button to create a task into your project.',
}, {
    trigger: 'div[name="name"] > input',
    content: 'Select the name of the task (e.g. Onboarding)',
    run: 'text Onboarding',
}, {
    trigger: 'button.o_kanban_edit',
    content: 'Click on Edit button to enter to the form view of the task.',
    position: 'bottom',
}, {
    trigger: 'div[name="partner_id"] input',
    content: Markup('Select the customer of your Sales Order <i>(e.g. Brandon Freeman)</i>. Since we have a Sales Order for this customer with a prepaid service product which the remaining hours to deliver is greater than 0, the Sales Order Item in the task should be contain the Sales Order Item containing this prepaid service product.'),
    run: 'text Brandon Freeman',
}, {
    trigger: 'div[name="partner_id"] ul > li:first-child > a:contains(Freeman)',
    content: 'Select the customer in the autocomplete dropdown.',
}, {
    trigger: 'a.nav-link:contains(Timesheets)',
    extra_trigger: 'div.o_notebook_headers',
    content: 'Click on Timesheets page to log a timesheet',
}, {
    trigger: 'div[name="timesheet_ids"] td.o_field_x2many_list_row_add a[role="button"]',
    content: 'Click on Add a line to create a new timesheet into the task.',
}, {
    trigger: 'div[name="unit_amount"] input',
    content: 'Enter one hour for this timesheet',
    run: 'text 1',
}, {
    trigger: 'i.o_optional_columns_dropdown_toggle',
    content: 'The so_line field should be hidden by default. We check if it is the case by adding this field in the timesheet list view',
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
}, {
    trigger: '.dropdown-item[data-menu-xmlid="project.menu_projects_config"]',
    content: 'Select Configuration > Projects.',
}, {
    trigger: 'button.o_list_button_add',
    content: 'Click on Create button to create a new project and see the different configuration available for the project.',
}, {
    trigger: 'a.nav-link[name="settings"]',
    extra_trigger: 'div.o_notebook_headers',
    content: 'Click on Settings page to check the allow_billable checkbox',
}, {
    trigger: 'div[name="allow_billable"] input',
    content: 'Check the allow_billable',
    run: function (actions) {
        if (!this.$anchor.prop('checked')) {
            actions.click(this.$anchor);
        }
    }
}, {
    trigger: 'div[name="partner_id"] input',
    content: Markup('Add the customer for this project to select an SO and SOL for this customer <i>(e.g. Brandon Freeman)</i>.'),
    run: 'text Brandon Freeman',
}, {
    trigger: 'div[name="partner_id"] ul > li:first-child > a:contains(Freeman)',
    content: 'Select the customer in the autocomplete dropdown',
}, {
    trigger: 'a.nav-link[name="billing_employee_rate"]',
    extra_trigger: 'div.o_notebook_headers',
    content: 'Click on Invoicing tab to configure the invoicing of this project.',
}, {
    trigger: 'div[name="sale_line_id"] input',
    content: 'Select a Sales Order Item as Default Sales Order Item for each task in this project.',
    run: 'text S',
}, {
    trigger: '[name="sale_line_id"] ul.ui-autocomplete > li:first-child > a:not(:has(i.fa))',
    content: 'Select the Sales Order Item in the autocomplete dropdown.',
}, {
    trigger: 'div[name="sale_line_employee_ids"] td.o_field_x2many_list_row_add > a[role="button"]',
    content: 'Click on Add a line on the mapping list view.',
}, {
    trigger: 'div[name="sale_line_employee_ids"] div[name="employee_id"] input',
    content: 'Select an employee to link a Sales Order Item on his timesheets into this project.',
    run: 'click',
}, {
    trigger: '[name="employee_id"] ul.ui-autocomplete > li:first-child > a:not(:has(i.fa))',
    content: 'Select the first employee in the autocomplete dropdown',
}, {
    trigger: 'div[name="sale_line_employee_ids"] div[name="sale_line_id"] input',
    content: 'Select the Sales Order Item to link to the timesheets of this employee.',
    position: 'bottom',
    run: 'text S',
}, {
    trigger: '[name=sale_line_id] ul.ui-autocomplete > li:first-child > a:not(:has(i.fa))',
    content: 'Select the first Sales Order Item in the autocomplete dropdown.',
    run: 'click'
}, {
    trigger: 'h1 > div[name="name"] > input',
    content: 'Set Project name',
    run: 'text Project with employee mapping',
}, {
    trigger: '.dropdown-item[data-menu-xmlid="project.menu_main_pm"]',
    content: 'Select Project main menu',
}, {
    trigger: '.oe_kanban_global_click :contains("Project for Freeman") button.o_dropdown_kanban',
    content: 'Open the project dropdown',
}, {
    trigger: '.o_kanban_record:contains("Project for Freeman") .dropdown-menu a:contains("Settings")',
    content: 'Start editing the project',
    // timer: 300,
}, {
    trigger: 'div[name="partner_id"] input',
    content: Markup('Add the customer for this project to select an SO and SOL for this customer <i>(e.g. Brandon Freeman)</i>.'),
    run: 'text Brandon Freeman',
}, {
    trigger: 'div[name="partner_id"] ul > li:first-child > a:contains(Freeman)',
    content: 'Select the customer in the autocomplete dropdown',
}, {
    trigger: 'a.nav-link[name="billing_employee_rate"]',
    extra_trigger: 'div.o_notebook_headers',
    content: 'Click on Invoicing tab to configure the invoicing of this project.',
}, {
    trigger: 'div[name="sale_line_id"] input',
    content: 'Select the first sale order of the list',
    run: 'text Prepaid',
}, {
    trigger: 'ul.ui-autocomplete > li:first-child > a:not(:has(i.fa))',
    content: 'Select the first item on the autocomplete dropdown',
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
    trigger: ".o_rightpanel_section[name='sales'] .o_rightpanel_title:contains('Sales')",
    content: 'Check the user sees Sales section',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section[name='sales'] .o_rightpanel_data:contains('Prepaid Hours')",
    content: 'Check the user sees a line in the Sales section',
    // timer: 300,
    run: function () {},
}, {
    trigger: ".o_rightpanel_section .oe_button_box .o_stat_text:contains('Sales Orders')",
    content: 'Check the user sees Sales Orders Stat Button',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section[name='profitability'] .o_rightpanel_title:contains('Profitability')",
    content: 'Check the user sees Profitability section',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section[name='profitability'] .o_rightpanel_data > .o_rightpanel_subsection:eq(0) > table > thead > tr > th:eq(0):contains('Revenues')",
    content: 'Check the user sees Profitability subsection row',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section[name='profitability'] .o_rightpanel_data > .o_rightpanel_subsection:eq(1) > table > thead > tr > th:eq(0):contains('Costs')",
    content: 'Check the user sees Profitability subsection row',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section[name='profitability'] .o_rightpanel_data > .o_rightpanel_subsection:eq(2) > table > thead > tr > th:eq(0):contains('Margin')",
    content: 'Check the user sees Profitability subsection row',
    run: function () {},
}, {
    trigger: ".o_rightpanel_section[name='milestones'] .o_rightpanel_title:contains('Milestones')",
    content: 'Check the user sees Milestones section',
}, {
    trigger: ".o_add_milestone a",
    content: "Add a first milestone",
}, {
    trigger: "div.o_field_widget[name=name] input",
    content: "Edit new Milestone",
    run: 'text New milestone',
}, {
    trigger: "div[name=deadline] .datetimepicker-input",
    content: "Edit new Milestone",
    run: 'text 12/12/2099',
}, {
    trigger: ".modal-footer button",
    content: "Save new Milestone",
}, {
    trigger: ".o-kanban-button-new",
    content: "Create new Project Update",
}, {
    trigger: "div.o_field_widget[name=name] input",
    content: "Give a name to Project Update",
    run: 'text New update',
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
// Those steps are currently needed in order to prevent the following issue:
// "Form views in edition mode are automatically saved when the page is closed, which leads to stray network requests and inconsistencies."
{
    trigger: '.o_back_button',
    content: 'Go back to the kanban view and the project update will be added on that view',
}, {
    trigger: '.o_controller_with_rightpanel',
    content: 'Check the kanban view of project update is rendered to be sure the user leaves the form view and the project update is created',
    run: function() {},
},
tour.stepUtils.toggleHomeMenu(),
...tour.stepUtils.goToAppSteps("project.menu_main_pm", 'Go to the Project app.'),
]);
});
