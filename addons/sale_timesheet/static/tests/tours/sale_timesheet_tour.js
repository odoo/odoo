odoo.define('sale_timesheet.tour', function (require) {
"use strict";

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
    trigger: 'ul.o_partner_autocomplete_dropdown > li:first-child > a',
    content: 'Select the first item on the autocomplete dropdown',
    run: 'click',
},
{
    trigger: 'td.o_field_x2many_list_row_add > a:first-child',
    content: 'Click on "Add a product" to add a new product. We will add a service product.',
    run: 'click',
}, {
    trigger: '.o_field_widget[name="product_id"], .o_field_widget[name="product_template_id"]',
    content: 'Select a prepaid service product <i>(e.g. Service Product (Prepaid Hours))</i>',
    run: function (actions) {
        actions.text('Service Product (Prepaid Hours)', this.$anchor.find('input'));
    },
}, {
    trigger: 'ul.ui-menu.ui-widget.ui-autocomplete > li:first-child > a',
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
    content: 'Click on Save button to save the Sales Order.',
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
    trigger: 'div[name="allow_billable"] input',
    content: 'Click on the checkbox to have a billable project.',
    run: 'click',
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
    content: 'Select the customer of your Sales Order <i>(e.g. Brandon Freeman)</i>. Since we have a Sales Order for this customer with a prepaid service product which the remaining hours to deliver is greater than 0, the Sales Order Item in the task should be contain the Sales Order Item containing this prepaid service product.',
    run: function (actions) {
        actions.text('Brandon Freeman', this.$anchor.find('input'));
    },
}, {
    trigger: 'ul.o_partner_autocomplete_dropdown > li:first-child > a',
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
    trigger: 'a[data-menu-xmlid="project.menu_project_config"]',
    content: 'Click on the Configuration menu.',
    run: 'click',
}, {
    trigger: 'a[role="menuitem"][data-menu-xmlid="project.menu_projects_config"]',
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
    trigger: 'div.o_notebook_headers',
    content: 'Click on Invoicing tab to configure the invoicing of this project.',
    run: function (actions) {
        const notebookId = $('div[name="pricing_type"]').closest("div.tab-pane").attr('id');
        actions.click(this.$anchor.find(`a[data-toggle="tab"][href="#${notebookId}"]`));
    },
}, {
    trigger: 'div[name="pricing_type"]',
    content: 'Check if the pricing type is equal to Task Rate',
    run: function (actions) {
        const pricingType = this.$anchor.find('input[data-value="task_rate"]').attr('checked');
        if (!pricingType)
            console.error('The default pricing type of the project should be "Task Rate".');
    }
}, {
    trigger: 'input[data-value="fixed_rate"]',
    content: 'Change the pricing type to "Project Rate"',
    run: 'click',
}, {
    trigger: 'div[name="partner_id"]',
    content: 'Add the customer for this project to select an SO and SOL for this customer <i>(e.g. Brandon Freeman)</i>.',
    run: function (actions) {
        actions.text('Azure Interior, Brandon Freeman', this.$anchor.find('input'));
    },
}, {
    trigger: 'ul.o_partner_autocomplete_dropdown > li:first-child > a',
    content: 'Select the customer in the autocomplete dropdown',
    run: 'click',
}, {
    trigger: 'div[name="sale_order_id"]',
    content: 'Select the first Sales Order for this customer to select a SOL.',
    run: function (actions) {
        actions.text('S', this.$anchor.find('input'));
    },
}, {
    trigger: 'ul.ui-autocomplete > li:first-child > a',
    content: 'Select the Sales Order in autocomplete dropdown.',
    run: 'click',
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
    trigger: 'input[data-value="employee_rate"]',
    content: 'Select "Employee rate" as pricing type.',
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
}]);

});
