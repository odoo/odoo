odoo.define('test_main_flows.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('main_flow_tour', {
    test: true,
    url: "/web",
}, [tour.STEPS.MENU_MORE, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"], .oe_menu_toggler[data-menu-xmlid="sale.sale_menu_root"]',
    content: _t('Organize your sales activities with the <b>Sales app</b>.'),
    position: 'bottom',
}, {
// Add Stockable product
    edition: "enterprise",
    trigger: ".o_menu_sections a:contains('Catalog')",
    extra_trigger: '.o_main_navbar',
    content: _t("Let\'s create products."),
    position: "bottom",
}, {
    trigger: ".o_menu_sections a:has(span:contains('Products')), .oe_secondary_submenu .oe_menu_text:contains('Products'):first",
    content: _t("Let\'s create products."),
    position: "bottom"
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_view',
    content: _t('Let\'s create your first product.'),
    position: 'right',
}, {
    trigger: 'input[name=name]',
    extra_trigger: '.o_form_sheet',
    content: _t('Let\'s enter the name.'),
    position: 'left',
    run: 'text the_flow.product',
}, {
    trigger:  "select[name=type]",
    content: _t('Let\'s enter the product type'),
    position: 'left',
    run: 'text "product"',
}, {
    trigger: '.o_notebook a:contains("Inventory")',
    content: _t('Go to inventory tab'),
    position: 'top',
}, {
    trigger: '.o_field_widget[name=route_ids] .o_checkbox + label:contains("Manufacture")',
    content: _t('Check Manufacture'),
    position: 'right',
}, {
    trigger: '.o_field_widget[name=route_ids] .o_checkbox + label:contains("Buy")',
    content: _t('Uncheck Buy'),
    position: 'right',
}, {
    trigger: '.o_field_widget[name=route_ids] .o_checkbox + label:contains("Make To Order")',
    content: _t('Uncheck  Make To Order'),
    position: 'right',
}, {
    trigger: '.o_form_button_save',
    content: _t('Save this product and the modifications you\'ve made to it.'),
    position: 'bottom',
}, {
    trigger: ".oe_button_box .oe_stat_button:has(div[name=bom_count])",
    extra_trigger: '.o_form_readonly',
    content: _t('See Bill of material'),
    position: 'bottom',
}, {
    trigger: ".o_list_button_add",
    content: _t("Let's create a new bill of material"),
    position: "right",
}, {
// Add first component
    trigger: ".o_field_x2many_list_row_add > a",
    extra_trigger: ".o_form_editable",
    content: _t("Click here to add some lines."),
    position: "bottom",
}, {
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: "text the_flow.component1",
}, {
    trigger: ".ui-menu-item > a:contains('the_flow.component1')",
    auto: true,
}, {
// Edit first component
    trigger: ".o_selected_row .o_external_button",
    content: _t("Click here to edit your component"),
    position: "right",
}, {
    trigger: '.o_notebook a:contains("Inventory")',
    content: _t('Go to inventory tab'),
    position: 'top',
}, {
    trigger: '.o_field_widget[name=route_ids] .o_checkbox + label:contains("Make To Order")',
    content: _t('Check Make To Order'),
    position: 'right',
}, {
    trigger: '.o_notebook a:contains("Purchase")',
    content: _t('Go to purchase tab'),
    position: 'top',
}, {
    trigger:  ".o_field_widget[name=seller_ids] .o_field_x2many_list_row_add > a",
    content: _t('Let\'s enter the cost price'),
    position: 'right',
}, {
    trigger:  ".o_field_widget[name=name] input",
    extra_trigger: ".modal-dialog",
    content: _t('Select a seller'),
    position: 'top',
    run: "text the_flow.vendor",
}, {
    trigger: ".ui-menu-item > a:contains('the_flow.vendor')",
    in_modal: false,
}, {
    trigger:  ".o_field_widget[name=price]",
    content: _t('Set the cost price'),
    position: 'right',
    run: "text 1",
}, {
    trigger:  ".modal-footer .btn-primary:first",
    extra_trigger: ".o_field_widget[name=name] > .o_external_button", // Wait name_create
    content: _t('Save & Close'),
    position: 'bottom',
}, {
    trigger: ".modal-footer .btn-primary",
    content: _t('Save'),
    position: 'bottom',
}, {
// Add second component
    trigger: ".o_field_x2many_list_row_add > a",
    extra_trigger: "body:not(.modal-open)",
    content: _t("Click here to add some lines."),
    position: "bottom",
}, {
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    extra_trigger: '.o_field_widget[name=bom_line_ids] .o_data_row:nth(1).o_selected_row',
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: "text the_flow.component2",
}, {
    trigger: ".ui-menu-item > a:contains('the_flow.component2')",
    auto: true,
}, {
// Edit second component
    trigger: ".o_selected_row .o_external_button",
    content: _t("Click here to edit your component"),
    position: "right",
}, {
    trigger: '.o_notebook a:contains("Purchase")',
    content: _t('Go to purchase tab'),
    position: 'top',
}, {
    trigger:  ".o_field_widget[name=seller_ids] .o_field_x2many_list_row_add > a",
    content: _t('Let\'s enter the cost price'),
    position: 'right',
}, {
    trigger:  ".o_field_widget[name=name] input",
    extra_trigger: ".modal-dialog",
    content: _t('Select a seller'),
    position: 'top',
    run: "text the_flow.vendor",
}, {
    trigger: ".ui-menu-item > a:contains('the_flow.vendor')",
    auto: true,
    in_modal: false,
}, {
    trigger:  ".o_field_widget[name=price]",
    content: _t('Set the cost price'),
    position: 'right',
    run: "text 1",
}, {
    trigger:  ".modal-footer .btn-primary:first",
    content: _t('Save & Close'),
    position: 'bottom',
}, {
    trigger: ".modal-footer .btn-primary",
    // Wait Save & Close and check value
    extra_trigger: ".o_field_widget[name=seller_ids] .o_data_row td:nth-child(2):contains('the_flow.vendor')",
    content: _t('Save'),
    position: 'bottom',
}, {
    trigger: '.o_form_button_save',
    extra_trigger: ".o_field_widget[name=bom_line_ids] .o_list_view tr:nth-child(3):has(.o_field_x2many_list_row_add)",
    content: _t('Save the bom.'),
    position: 'bottom',
}, {
    trigger: ".breadcrumb li:first",
    extra_trigger: ".o_form_readonly", // FIXME: this is required due to an issue in tour_manager (see [*])
    content: _t("Use the breadcrumbs to <b>go back to products</b>."),
    position: "bottom"
}, {
// Add service product
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_view',
    content: _t('Let\'s create your second product.'),
    position: 'right',
}, {
    trigger: 'input[name=name]',
    extra_trigger: '.o_form_sheet',
    content: _t('Let\'s enter the name.'),
    position: 'left',
    run: 'text the_flow.service',
}, {
    trigger: '.o_field_widget[name=type]',
    content: _t('Set to service'),
    position: 'left',
    run: 'text "service"',
}, {
    trigger: '.o_notebook a:contains("Invoicing")',
    content: _t('Go to invoicing tab'),
    position: 'bottom',
}, {
    trigger: '.o_field_widget[name=service_policy] .o_radio_input[data-value="delivered_timesheet"]',
    content: _t('Change service policy'),
    position: 'left',
}, {
    trigger: '.o_field_widget[name=service_tracking] input[data-value="task_global_project"]',
    content: _t('Change track service'),
    position: 'left',
}, {
    trigger: '.o_field_widget[name=project_id] input',
    content: _t('Choose project'),
    position: 'left',
    run: 'text the_flow.project',
}, {
    trigger: ".ui-menu-item > a:contains('the_flow.project')",
    auto: true,
}, {
    trigger: '.o_form_button_save',
    extra_trigger: '.o_field_widget[name=project_id] > .o_external_button', // Wait name_create
    content: _t('Save this product and the modifications you\'ve made to it.'),
    position: 'bottom',
}, {
// Create an opportunity
    edition: "enterprise",
    trigger: '.o_menu_toggle',
    content: _t('Go back to the app switcher'),
    position: 'bottom',
}, {
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"], .oe_menu_toggler[data-menu-xmlid="crm.crm_menu_root"]',
    content: _t('Organize your sales activities with the <b>CRM app</b>.'),
    position: 'bottom',
}, {
    trigger: ".o-kanban-button-new",
    extra_trigger: '.o_opportunity_kanban',
    content: _t("Click here to <b>create your first opportunity</b> and add it to your pipeline."),
    position: "right"
}, {
    trigger: ".modal-body input:first",
    content: _t("Enter the opportunity title."),
    position: "right",
    run: "text the_flow.opportunity",
}, {
    trigger: ".o_field_widget[name=partner_id] input",
    content: _t("Write the name of your customer to create one on the fly, or select an existing one."),
    position: "left",
    run: "text the_flow.customer",
}, {
    trigger: ".ui-menu-item > a:contains('the_flow.customer')",
    in_modal: false,
    auto: true,
}, {
    trigger: ".modal-footer .btn-primary",
    extra_trigger: ".o_field_widget[name=partner_id] > .o_external_button", // Wait name_create
    content: _t("Create"),
    position: "bottom",
}, {
    trigger: ".o_kanban_group:first-child .o_kanban_record:last-child",
    content: _t("<b>Drag &amp; drop opportunities</b> between columns as you progress in your sales cycle."),
    position: "right",
    run: "drag_and_drop .o_opportunity_kanban .o_kanban_group:eq(2) ",
}, {
    trigger: ".o_kanban_record:has(span:contains('the_flow.opportunity'))",
    extra_trigger: ".o_kanban_group:eq(2) > .o_kanban_record:has(span:contains('the_flow.opportunity'))", // FIXME: this is required due to an issue in tour_manager (see [*])
    content: _t("Click on an opportunity to zoom to it."),
    position: "bottom",
}, {
// Create a quotation
    trigger: ".o_statusbar_buttons > button:enabled:contains('New Quotation')",
    content: _t('<p><b>Create a quotation</p>'),
    position: "right"
}, {
    trigger: ".o_field_widget[name=order_line] .o_field_x2many_list_row_add > a",
    content: _t("Click here to add some lines to your quotations."),
    position: "bottom",
}, {
    trigger: ".o_field_widget[name=product_id] input",
    content: _t("Select a product, or create a new one on the fly. The product will define the default sales price (that you can change), taxes and description automatically."),
    position: "right",
    run: "text the_flow.product",
}, {
    trigger: ".ui-menu-item > a:contains('the_flow.product')",
    auto: true,
    in_modal: false,
    run: function (actions) {
        actions.auto();
        // if the one2many isn't editable, we have to close the dialog
        if ($(".modal-footer .btn-primary").length) {
            actions.auto(".modal-footer .btn-primary");
        }
    },
}, {
    trigger: ".o_field_widget[name=order_line] .o_field_x2many_list_row_add > a",
    content: _t("Click here to add some lines to your quotations."),
    position: "bottom",
}, {
    trigger: ".o_field_widget[name=product_id] input",
    // the one2many may be editable or not according to the modules installed, so
    // we have to handle both cases
    extra_trigger: '.o_field_widget[name=order_line] .o_data_row:nth(1).o_selected_row, .modal-dialog',
    content: _t("Select a product"),
    position: "right",
    run: "text the_flow.service",
}, {
    trigger: ".ui-menu-item > a:contains('the_flow.service')",
    auto: true,
    in_modal: false,
    run: function (actions) {
        actions.auto();
        // if the one2many isn't editable, we have to close the dialog
        if ($(".modal-footer .btn-primary").length) {
            actions.auto(".modal-footer .btn-primary");
        }
    },
}, {
    trigger: ".o_statusbar_buttons > button.o_sale_print:enabled",
    content: _t("<p><b>Print this quotation.</b></p>"),
    position: "bottom"
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Send by Email')",
    extra_trigger: ".o_statusbar_status .btn-primary:contains('Quotation Sent')",
    content: _t("Try to send it to email"),
    position: "bottom",
}, {
    trigger: ".o_field_widget[name=email]",
    content: _t("Enter an email address"),
    position: "right",
    run: "text test@the_flow.com",
}, {
    trigger: ".modal-footer .btn-primary",
    content: _t("Save your changes"),
    position: "bottom",
}, {
    trigger: ".modal-footer .btn-primary span:contains('Send')",
    content: _t("Try to send it to email"),
    position: "bottom",
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Confirm Sale')",
    content: _t("<p>Confirm this quotation</p>"),
    position: "bottom"
}, {
    trigger: ".o_form_button_save",
    extra_trigger: ".o_statusbar_status .btn-primary:contains('Sales Order')",
    content: _t("<p>Save this quotation</p>"),
    position: "bottom"
// Reordering rule
}, {
    edition: "enterprise",
    trigger: '.o_menu_toggle',
    content: _t('Go back to the app switcher'),
    position: 'bottom',
}, {
    trigger: '.o_app > div:contains("Inventory"), .oe_menu_toggler:contains("Inventory")',
    content: _t('Go to Inventory'),
    position: 'bottom',
}, {
    edition: "enterprise",
    trigger: ".o_menu_sections a:contains('Master Data')",
    content: _t("Go to Master Data"),
    position: "bottom"
}, {
    trigger: ".o_menu_sections a[data-menu-xmlid='stock.menu_reordering_rules_config'], .oe_secondary_submenu a[data-menu-xmlid='stock.menu_reordering_rules_config']",
    content: _t("Reordering Rules"),
    position: "bottom"
}, {
    trigger: ".o_list_button_add",
    content: _t("Let's create a new reordering rule"),
    position: "right",
}, {
    trigger: ".o_field_widget[name=product_id] input",
    content: _t("Write the name of your product."),
    position: "top",
    run: "text the_flow.component2",
}, {
    trigger: ".ui-menu-item > a:contains('the_flow.component2')",
    auto: true,
}, {
    trigger: ".o_field_widget[name=product_min_qty]",
    content: _t("Set the minimum product quantity"),
    position: "right",
    run: 'text 1',
}, {
    trigger: ".o_field_widget[name=product_max_qty]",
    content: _t("Set the maximum product quantity"),
    position: "right",
    run: 'text 10',
}, {
    trigger: ".o_form_button_save",
    content: _t("<p>Save this reordering rule</p>"),
    position: "bottom"
}, {
// Run the schedulers
    edition: "enterprise",
    trigger: ".o_menu_sections a:contains('Operations')",
    content: _t("Go to Run Schedulers"),
    position: "bottom"
},{
    trigger: ".o_menu_sections a[data-menu-xmlid='stock.menu_procurement_compute'], .oe_secondary_submenu a[data-menu-xmlid='stock.menu_procurement_compute']",
    content: _t("Click on schedulers"),
    position: "bottom"
}, {
    trigger: ".modal-footer .btn-primary",
    extra_trigger: ".modal-dialog",
    content: _t("Run Schedulers"),
    position: "bottom",
}, {
//Go to purchase:
    edition: "enterprise",
    trigger: '.o_menu_toggle',
    content: _t('Go back to the app switcher'),
    position: 'bottom',
}, {
    trigger: '.o_app > div:contains("Purchases"), .oe_menu_toggler:contains("Purchases")',
    content: _t('Go to Purchase'),
    position: 'bottom',
}, {
    trigger: '.o_data_row:has(.o_data_cell:contains("the_flow.vendor"))',
    content: _t('Select the generated request for quotation'),
    position: 'bottom',
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Confirm Order')",
    content: _t("Confirm quotation"),
    position: "bottom",
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Receive Products')",
    content: _t("Receive Product"),
    position: "bottom",
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Validate')",
    content: _t("Validate"),
    position: "bottom",
}, {
    trigger: ".modal-footer .btn-primary",
    extra_trigger: ".modal-dialog",
    content: _t("Apply"),
    position: "bottom",
}, {
    trigger: ".o_back_button a, .breadcrumb li:not('.active'):last",
    content: _t('go back to the purchase order'),
    position: 'bottom',
 }, {
    trigger: ".oe_button_box .oe_stat_button:has(div[name=invoice_count])",
    content: _t('go to Vendor Bills'),
    position: 'bottom',
}, {
    trigger: ".o_list_button_add",
    content: _t("Let's create a new vendor bill"),
    position: "right",
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Validate')",
    content: _t("Try to send it to email"),
    position: "bottom",
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Register Payment')",
    content: _t("Register Payment"),
    position: "bottom",
}, {
    trigger: "select.o_field_widget[name=journal_id]",
    extra_trigger: ".modal-dialog",
    content: _t("Select Journal"),
    position: "bottom",
    run: 'text(Bank (USD))',
}, {
    trigger: ".modal-footer .btn-primary",
    extra_trigger: ".o_field_widget[name=payment_method_id]", // FIXME: Wait onchange
    content: _t("Validate"),
    position: "bottom",
}, {
    edition: "enterprise",
    trigger: '.o_menu_toggle',
    content: _t('Go back to the app switcher'),
    position: 'bottom',
}, {
    trigger: '.o_app > div:contains("Manufacturing"), .oe_menu_toggler:contains("Manufacturing")',
    content: _t('Go to Manufacturing'),
    position: 'bottom',
}, {
    trigger: '.o_data_row:has(.o_data_cell:contains("the_flow.product")):first',
    content: _t('Select the generated manufacturing order'),
    position: 'bottom',
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Check availability')",
    content: _t("Check availability"),
    position: "bottom",
}, {
    trigger: ".o_statusbar_buttons > button.oe_highlight:enabled:contains('Produce')",
    content: _t("Produce"),
    position: "bottom",
}, {
    trigger:  ".modal-footer .btn-primary:first",
    content: _t('Record Production'),
    position: 'bottom',
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Mark as Done')",
    content: _t("Mark as Done"),
    position: "bottom",
}, {
    edition: "enterprise",
    trigger: '.o_menu_toggle',
    content: _t('Go back to the app switcher'),
    position: 'bottom',
}, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"], .oe_menu_toggler[data-menu-xmlid="sale.sale_menu_root"]',
    content: _t('Organize your sales activities with the <b>Sales app</b>.'),
    position: 'bottom',
}, {
    edition: "enterprise",
    trigger: ".o_menu_sections a[data-menu-xmlid='sale.sale_order_menu']",
    content: _t("Go to Sales menu"),
    position: "bottom"
}, {
    trigger: ".o_menu_sections a[data-menu-xmlid='sale.menu_sale_order'], .oe_secondary_submenu a[data-menu-xmlid='sale.menu_sale_order']",
    content: _t("Go to the sales orders"),
    position: "bottom"
}, {
    trigger: ".o_data_row:first",
    extra_trigger: '.o_control_panel > .breadcrumb:contains("Sales Orders")',
    content: _t("Go to the last sale order"),
    position: "right"
}, {
    trigger: '.oe_button_box .oe_stat_button:has(div[name=tasks_count])',
    content: _t('See Tasks'),
    position: 'right',
}, {
    trigger: '.o_field_widget[name=project_id]',
    content: _t('See Project'),
    position: 'right',
}, {
    trigger: '.oe_button_box .oe_stat_button:has(span:contains("Timesheets"))',
    extra_trigger: '.o_form_readonly',
    content: _t('See Timesheets'),
    position: 'bottom',
}, {
    trigger: '.o_list_button_add',
    content: _t('Add a Timesheet'),
    position: 'bottom',
}, {
    trigger: '.o_selected_row input[name=name]',
    content: _t('Set description'),
    position: 'bottom',
    run: 'text 10 hours',
}, {
    trigger: '.o_selected_row .o_field_widget[name=task_id] input',
    content: _t('Choose a task'),
    position: 'bottom',
    run: 'click',
}, {
    trigger: ".ui-menu-item > a",
    auto: true,
}, {
    trigger: '.o_selected_row input[name=unit_amount]',
    content: _t('Set time'),
    position: 'bottom',
    run: 'text 10',
}, {
    trigger: '.o_list_button_save',
    content: _t('Save'),
    position: 'bottom',
}, {
    trigger: '.breadcrumb li:nth-child(2) a',
    extra_trigger: '.o_list_button_add', // Waiting save
    content: _t('Back to the sale order'),
    position: 'bottom',
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Create Invoice')",
    content: _t("Validate"),
    position: "bottom",
}, {
    trigger: ".modal-footer .btn-primary",
    content: _t("Create and View Invoices"),
    position: "bottom",
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Validate')",
    content: _t("Validate"),
    position: "bottom",
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Register Payment')",
    content: _t("Register Payment"),
    position: "bottom",
}, {
    trigger: "select.o_field_widget[name=journal_id]",
    extra_trigger: ".modal-dialog",
    content: _t("Select Journal"),
    position: "bottom",
    run: 'text(Bank (USD))',
}, {
    trigger: ".modal-footer .btn-primary",
    content: _t("Validate"),
    position: "bottom",
}, {
    edition: "enterprise",
    trigger: '.o_menu_toggle',
    content: _t('Go back to the app switcher'),
    position: 'bottom',
}, {
    edition: "enterprise",
    trigger: '.o_app[data-menu-xmlid="account.menu_finance"], .oe_menu_toggler[data-menu-xmlid="account.menu_finance"]',
    content: _t('Go to Accounting'),
    position: 'bottom',
}, {
    edition: "enterprise",
    trigger: 'div[name=bank_journal_default_cta] > a[data-name=create_bank_statement], div[name=bank_journal_cta] > a[data-name=create_bank_statement]',
    content: _t('Create a new bank statement'),
    position: 'bottom',
}, {
    edition: "enterprise",
    trigger: 'input[name=name]',
    content: _t('Let\'s enter the reference.'),
    position: 'left',
    run: 'text the_flow.statement',
}, {
    edition: "enterprise",
    trigger:  ".o_field_widget[name=balance_end_real] input",
    content: _t('Let\'s calculate the ending balance.'),
    position: 'right',
    run: 'text 9010.85', // + 12.65
}, {
    edition: "enterprise",
    trigger:  ".o_field_widget[name=line_ids] .o_field_x2many_list_row_add > a",
    content: _t("Click here to add some lines."),
    position: "bottom",
}, {
    edition: "enterprise",
    trigger: ".o_selected_row .o_field_widget[name=amount] input",
    content: _t("Write the amount received."),
    position: "bottom",
    run: "text 12.65",
}, {
    edition: "enterprise",
    trigger: ".o_selected_row .o_field_widget[name=partner_id] input",
    content: _t("Write the name of your customer."),
    position: "bottom",
    run: "text the_flow.customer",
}, {
    edition: "enterprise",
    trigger: ".ui-menu-item > a:contains('the_flow.customer')",
    auto: true,
}, {
    edition: "enterprise",
    trigger: ".o_selected_row .o_field_widget[name=name]",
    extra_trigger: ".o_selected_row .o_field_widget[name=partner_id] .o_external_button", // FIXME: this is required due to an issue in tour_manager (see [*])
    content: _t('Let\'s enter a name.'),
    position: "bottom",
    run: "text the_flow.statement.line",
}, {
    edition: "enterprise",
    trigger: '.o_form_button_save',
    content: _t('Save.'),
    position: 'bottom',
}, {
    edition: "enterprise",
    trigger: ".o_statusbar_buttons > button:enabled:contains('Reconcile')",
    content: _t('<p><b>Reconcile</p>'),
    position: "bottom",
}, {
    edition: "enterprise",
    trigger: "button.o_reconcile",
    content: _t('<p><b>Click on Reconcile</p>'),
    position: "right",
}, {
    edition: "enterprise",
    trigger: ".button_close_statement",
    content: _t('<p><b>Close this statement.</p>'),
    position: "bottom",
}]);
});

/*
 * [*] FIXME: issue in tour_manager:
 *     The JQuery element of a step is registered as soon as its trigger and
 *     extra_trigger elements are visible in the DOM, but it's action is delayed
 *     to handle the 'running_step_delay' option (0 by default, but even with 0,
 *     the action is executed after finishing the current execution block, which
 *     may produce a re-rendering of the part of the DOM containing the element).
 *     When this happens, the action is executed on an jquery element not present
 *     in the DOM anymore.
 *     To avoid this, we add an 'extra_trigger' to wait for the updated jquery
 *     element before activating the step (and thus registering the JQuery element).
 */
