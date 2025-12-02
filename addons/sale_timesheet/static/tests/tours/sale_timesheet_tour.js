import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('sale_timesheet_tour', {
    url: '/odoo',
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.selectCustomer("Brandon Freeman"),
        ...tourUtils.addProduct("Service Product (Prepaid Hours)"),
{
    trigger: 'div[name="product_uom_qty"] input',
    content: "Add 10 hours as ordered quantity for this product.",
    run: "edit 10 && press Tab",
}, {
    trigger: '.o_field_cell[name=price_subtotal]:contains(2,500.00)',
}, {
    trigger: "button[name=action_confirm]:enabled",
    content: 'Click on Confirm button to create a sale order with this quotation.',
    run: "click",
}, {
    content: 'Wait for the confirmation to finish. State should be "Sales Order"',
    trigger: '.o_field_widget[name=state] .o_arrow_button_current:contains("Sales Order")',
},
...stepUtils.toggleHomeMenu(),
...stepUtils.goToAppSteps("project.menu_main_pm", 'Go to the Project app.'),
{
    trigger: 'button.o-kanban-button-new',
    content: 'Add a new project.',
    run: "click",
}, {
    isActive: ['button.o-kanban-button-new.dropdown'], // if the project template dropdown is active
    trigger: 'button.o-dropdown-item:contains("New Project")',
    content: 'Let\'s create a regular project.',
    tooltipPosition: 'right',
    run: "click",
}, {
    trigger: '.o_field_widget.o_project_name input',
    content: 'Select your project name (e.g. Project for Freeman)',
    run: "edit Project for Freeman",
}, {
    trigger: 'div[name="allow_billable"] input',
    run: 'click',
}, {
    trigger: 'button[name="action_view_tasks"]',
    content: 'Click on Create button to create and enter to this newest project.',
    run: "click",
}, {
    trigger: ".breadcrumb-item.o_back_button",
    run: "click",
}, {
    trigger: ".o_kanban_record:contains('Project for Freeman')",
}, {
    trigger: ".o_switch_view.o_list",
    run: "click",
}, {
    trigger: "tr.o_data_row td[name='name']:contains('Project for Freeman')",
    run: "click",
}, {
    trigger: ".nav-link:contains('Settings')",
    run: "click",
}, {
    trigger: "div[name='allow_milestones'] input",
    run: "click",
}, {
    trigger: "button[name='action_view_tasks']",
    run: "click",
}, {
    trigger: 'div.o_kanban_header > div:first-child input',
    content: 'Select a name of your kanban column (e.g. To Do)',
    run: "edit To Do",
}, {
    trigger: 'button.o_kanban_add',
    content: 'Click on Add button to create the column.',
    run: "click",
},{
    content: "wait the new column is created",
    trigger: ".o_kanban_renderer .o_kanban_group .o_kanban_header_title:contains(to do)",
},{
    trigger: 'button.o-kanban-button-new',
    content: 'Click on Create button to create a task into your project.',
    run: "click",
}, {
    trigger: 'div[name="display_name"] > input',
    content: 'Select the name of the task (e.g. Onboarding)',
    run: "edit Onboarding",
}, {
    trigger: 'button.o_kanban_edit',
    content: 'Click on Edit button to enter to the form view of the task.',
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: 'div[name="partner_id"] input',
    content: markup('Select the customer of your Sales Order <i>(e.g. Brandon Freeman)</i>. Since we have a Sales Order for this customer with a prepaid service product which the remaining hours to deliver is greater than 0, the Sales Order Item in the task should be contain the Sales Order Item containing this prepaid service product.'),
    run: "edit Brandon Freeman",
}, {
    trigger: 'div[name="partner_id"] ul > li:first-child > a:contains(Freeman)',
    content: 'Select the customer in the autocomplete dropdown.',
    run: "click",
},
{
    trigger: "div.o_notebook_headers",
},
{
    trigger: 'a.nav-link:contains(Timesheets)',
    content: 'Click on Timesheets page to log a timesheet',
    run: "click",
}, {
    trigger: 'div[name="timesheet_ids"] td.o_field_x2many_list_row_add a[role="button"]',
    content: 'Click on Add a line to create a new timesheet into the task.',
    run: "click",
}, {
    trigger: '.o_field_x2many div[name="name"] input',
    content: 'Enter a description for this timesheet',
    run: "edit work",
}, {
    trigger: 'div[name="unit_amount"] input',
    content: 'Enter one hour for this timesheet',
    run: "edit 1",
}, {
    trigger: 'i.o_optional_columns_dropdown_toggle',
    content: 'The so_line field should be hidden by default. We check if it is the case by adding this field in the timesheet list view',
    run: "click",
}, {
    trigger: 'input[name="so_line"]',
    content: 'Check the so_line field to display the column on the list view.',
    run: function (actions) {
        if (!this.anchor.checked) {
            actions.click();
        }
    },
}, {
    trigger: 'button.o_form_button_save i',
    content: 'Manually save the records (sale order should be filled based on the partner picked for this task',
    run: "click",
}, {
    trigger: 'button[name="action_view_so"]',
    content: 'Click on this stat button to see the SO linked to the SOL of the task.',
    run: "click",
}, {
    trigger: 'div[name="order_line"]',
    content: 'Check if the quantity delivered is equal to 1 hour.',
    run({ queryFirst }) {
        const header = this.anchor.querySelectorAll("thead > tr");
        if (!header || header.length === 0)
            console.error('No Sales Order Item is found in the Sales Order.');
        const tr = [...header][0];
        let index = -1;
        for (let i = 0; i < tr.children.length; i++) {
            const th = tr.children.item(i);
            if (th.dataset && th.dataset.name === 'qty_delivered')
                index = i;
        }
        const qtyDelivered = queryFirst(`tbody > tr:first-child > td.o_data_cell:eq(${index})`, { root: this.anchor });
        if (qtyDelivered.textContent !== "1.00")
            console.error('The quantity delivered on this Sales Order Item should be equal to 1.00 hour. qtyDelivered = ' + qtyDelivered);
    },
}, {
    trigger: 'button[data-menu-xmlid="project.menu_project_config"]',
    content: 'Click on the Configuration menu.',
    run: "click",
}, {
    trigger: '.dropdown-item[data-menu-xmlid="project.menu_projects_config"]',
    content: 'Select Configuration > Projects.',
    run: "click",
}, {
    trigger: 'button.o_list_button_add',
    content: 'Click on Create button to create a new project and see the different configuration available for the project.',
    run: "click",
}, {
    isActive: ['button.o_list_button_add.dropdown'], // if the project template dropdown is active
    trigger: 'button.o-dropdown-item:contains("New Project")',
    content: 'Let\'s create a regular project.',
    tooltipPosition: 'right',
    run: "click",
},
{
    trigger: "div.o_notebook_headers",
},
{
    trigger: 'a.nav-link[name="settings"]',
    content: 'Click on Settings page to check the allow_billable checkbox',
    run: "click",
}, {
    trigger: 'div[name="allow_billable"] input',
    content: 'Check the allow_billable',
    run: function (actions) {
        if (!this.anchor.checked) {
            actions.click();
        }
    }
}, {
    trigger: 'div[name="partner_id"] input',
    content: markup('Add the customer for this project to select an SO and SOL for this customer <i>(e.g. Brandon Freeman)</i>.'),
    run: "edit Brandon Freeman",
}, {
    trigger: 'div[name="partner_id"] ul > li:first-child > a:contains(Freeman)',
    content: 'Select the customer in the autocomplete dropdown',
    run: "click",
}, {
    trigger: 'div[name="sale_line_id"] input',
    content: 'Select a Sales Order Item as Default Sales Order Item for each task in this project.',
    run: "edit S",
}, {
    trigger: '[name="sale_line_id"] ul.ui-autocomplete > li:first-child > a:not(:has(i.fa))',
    content: 'Select the Sales Order Item in the autocomplete dropdown.',
    run: "click",
},
{
    trigger: "div.o_notebook_headers",
},
{
    trigger: 'a.nav-link[name="billing_employee_rate"]',
    content: 'Click on Invoicing tab to configure the invoicing of this project.',
    run: "click",
}, {
    trigger: 'div[name="sale_line_employee_ids"] td.o_field_x2many_list_row_add > a[role="button"]',
    content: 'Click on Add a line on the mapping list view.',
    run: "click",
}, {
    trigger: 'div[name="sale_line_employee_ids"] div[name="employee_id"] input',
    content: 'Select an employee to link a Sales Order Item on his timesheets into this project.',
    run: 'click',
}, {
    trigger: '[name="employee_id"] ul.ui-autocomplete > li:first-child > a:not(:has(i.fa))',
    content: 'Select the first employee in the autocomplete dropdown',
    run: "click",
}, {
    trigger: 'div[name="sale_line_employee_ids"] div[name="sale_line_id"] input',
    content: 'Select the Sales Order Item to link to the timesheets of this employee.',
    tooltipPosition: 'bottom',
    run: "edit S",
}, {
    trigger: '[name=sale_line_id] ul.ui-autocomplete > li:first-child > a:not(:has(i.fa))',
    content: 'Select the first Sales Order Item in the autocomplete dropdown.',
    run: "click",
}, {
    trigger: 'h1 > div[name="name"] > div > textarea',
    content: 'Set Project name',
    run: "edit Project with employee mapping",
}, {
    trigger: '[data-menu-xmlid="project.menu_projects"]',
    content: 'Select Project main menu',
    run: "click",
}, {
    trigger: ".o_switch_view.o_list",
    run: "click",
}, {
    trigger: "tr.o_data_row td[name='name']:contains('Project for Freeman')",
    run: "click",
}, {
    trigger: 'div[name="partner_id"] input',
    content: markup('Add the customer for this project to select an SO and SOL for this customer <i>(e.g. Brandon Freeman)</i>.'),
    run: "edit Brandon Freeman",
}, {
    trigger: 'div[name="partner_id"] ul > li:first-child > a:contains(Freeman)',
    content: 'Select the customer in the autocomplete dropdown',
    run: "click",
},
{
    trigger: "div.o_notebook_headers",
},
{
    trigger: 'a.nav-link[name="settings"]',
    content: 'Click on Settings tab to configure this project.',
    run: "click",
}, {
    trigger: 'div[name="sale_line_id"] input',
    content: 'Select the first sale order of the list',
    run: "edit Prepaid",
}, {
    trigger: 'ul.ui-autocomplete > li:first-child > a:not(:has(i.fa))',
    content: 'Select the first item on the autocomplete dropdown',
    run: "click",
}, {
    trigger: '[data-menu-xmlid="project.menu_projects"]',
    content: 'Select Project main menu',
    run: "click",
}, {
    trigger: '.o_kanban_record:contains("Project for Freeman")',
    content: 'Open the project',
    run: "click",
}, {
    trigger: ".o_control_panel_navigation button i.fa-sliders",
    content: 'Open embedded actions',
    run: "click",
}, {
    trigger: "span.o-dropdown-item:contains('Top Menu')",
    run: "click",
}, {
    trigger: ".o-dropdown-item div span:contains('Dashboard')",
    content: "Put Dashboard in the embedded actions",
    run: "click",
}, {
    trigger: ".o_embedded_actions button span:contains('Dashboard')",
    content: "Open Dashboard",
    run: "click",
}, {
    trigger: ".o_rightpanel_section[name='profitability'] .o_rightpanel_title:contains('Profitability')",
    content: 'Check the user sees Profitability section',
}, {
    trigger: ".o_rightpanel_section[name='profitability'] .o_rightpanel_data > div > .o_rightpanel_subsection:eq(0) > table > thead > tr > th:eq(0):contains('Revenues')",
    content: 'Check the user sees Profitability subsection row',
}, {
    trigger: "button.o_group_caret:has(.fa-caret-right)",
    content: 'Check that the dropdown button is present',
    run: "click",
}, {
    trigger: "th:contains('Sales Order Items')",
    content: 'Check that the sale items section is present',
}, {
    trigger: "button.o_group_caret:has(.fa-caret-down)",
    content: 'Check that the button has changed',
    run: "click",
}, {
    trigger: ".o_rightpanel_section[name='profitability'] .o_rightpanel_data > div > .o_rightpanel_subsection:eq(1) > table > thead > tr > th:eq(0):contains('Costs')",
    content: 'Check the user sees Profitability subsection row',
}, {
    trigger: ".o_rightpanel_section[name='profitability'] .o_rightpanel_data > div > .o_rightpanel_subsection:eq(2) > table > thead > tr > th:eq(0):contains('Total')",
    content: 'Check the user sees Profitability subsection row',
}, {
    trigger: ".o_rightpanel_section[name='milestones'] .o_rightpanel_title:contains('Milestones')",
    content: 'Check the user sees Milestones section',
    run: "click",
}, {
    trigger: ".o_add_milestone a",
    content: "Add a first milestone",
    run: "click",
}, {
    trigger: ".o_list_button_add",
    content: "Add a first milestone",
    run: "click",
}, {
    trigger: "div.o_field_widget[name=name] input",
    run: "edit New milestone",
}, {
    trigger: "input[data-field=deadline]",
    content: "Edit new Milestone",
    run: "edit 12/12/2099",
}, {
    trigger: ".o_list_button_save",
    content: "Save new Milestone",
    run: "click",
}, {
    trigger: ".breadcrumb-item.o_back_button",
    run: "click",
}, {
    trigger: ".o-kanban-button-new",
    content: "Create new Project Update",
    run: "click",
}, {
    trigger: "div.o_field_widget[name=name] input",
    content: "Give a name to Project Update",
    run: "edit New update",
}, {
    trigger: ".o_field_widget[name=description] h3:contains('Profitability')",
    content: "Profitability title must be in description",
}, {
    trigger: ".o_field_widget[name=description] h3:contains('Milestones')",
    content: "Milestones title must be in description",
},
// Those steps are currently needed in order to prevent the following issue:
// "Form views in edition mode are automatically saved when the page is closed, which leads to stray network requests and inconsistencies."
{
    trigger: '.o_back_button',
    content: 'Go back to the kanban view and the project update will be added on that view',
    run: "click",
}, {
    trigger: '.o_controller_with_rightpanel',
    content: 'Check the kanban view of project update is rendered to be sure the user leaves the form view and the project update is created',
},
...stepUtils.toggleHomeMenu(),
...stepUtils.goToAppSteps("project.menu_main_pm", 'Go to the Project app.'),
]});
