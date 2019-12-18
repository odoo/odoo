odoo.define('test_main_flows.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('main_flow_tour', {
    test: true,
    url: "/web",
}, [tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    content: _t('Organize your sales activities with the <b>Sales app</b>.'),
    position: 'right',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    content: _t('Organize your sales activities with the <b>Sales app</b>.'),
    position: 'bottom',
    edition: 'enterprise'
}, {
// Add Stockable product
    trigger: ".o_menu_sections a:contains('Products')",
    extra_trigger: '.o_main_navbar',
    content: _t("Let\'s create products."),
    position: "bottom",
}, {
    trigger: ".o_menu_sections a:has(span:contains('Products'))",
    content: _t("Let\'s create products."),
    position: "bottom"
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_view',
    content: _t('Let\'s create your first product.'),
    position: 'bottom',
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
    trigger: '.o_field_widget[name=route_ids] .custom-checkbox > label:contains("Manufacture")',
    content: _t('Check Manufacture'),
    position: 'right',
}, {
    trigger: '.o_field_widget[name=route_ids] .custom-checkbox > label:contains("Buy")',
    content: _t('Uncheck Buy'),
    position: 'right',
}, {
    trigger: '.o_field_widget[name=route_ids] .custom-checkbox > label:contains("Replenish on Order (MTO)")',
    content: _t('Uncheck  Replenish on Order (MTO)'),
    position: 'right',
}, {
    trigger: '.o_notebook a:contains("General Information")',
    content: _t('Go to main tab'),
    position: 'top',
}, {
    trigger: ".o_field_widget[name=taxes_id] input",
    content: _t("Focus on customer taxes field."),
    run: function (actions) {
        actions.click();
        var $e = $('.ui-menu-item:not(.o_m2o_dropdown_option) > a.ui-state-active');
        if ($e.length) {
            actions.click($e);
        } else {
            actions.click(); // close dropdown
        }
    },
}, {
    trigger: '.o_form_button_save',
    content: _t('Save this product and the modifications you\'ve made to it.'),
    position: 'bottom',
}, {
    trigger: ".oe_button_box",
    extra_trigger: '.o_form_readonly',
    auto: true,
    run: function (actions) {
        // auto expand "More" buttons
        var $more = $(".oe_button_box .o_button_more");
        if ($more.length) {
            actions.click($more);
        }
    },
},{
    trigger: ".oe_button_box .oe_stat_button:has(div[name=bom_count])",
    extra_trigger: '.o_form_readonly',
    content: _t('See Bill of material'),
    position: 'bottom',
}, {
    trigger: ".o_list_button_add",
    content: _t("Let's create a new bill of material"),
    position: "bottom",
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
    trigger: '.o_field_widget[name=route_ids] .custom-checkbox > label:contains("Replenish on Order (MTO)")',
    content: _t('Check Replenish on Order (MTO)'),
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
},
 {
// Add second component
    trigger: ".o_field_x2many_list_row_add > a",
    extra_trigger: "body:not(:has(table.o_list_table div.o_field_widget[name='product_id'] input))",
    content: _t("Click here to add some lines."),
    position: "bottom",
},
{
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    extra_trigger: '.o_field_widget[name=bom_line_ids] .o_data_row:nth(1).o_selected_row',
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: "text the_flow.component2",
},
{
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
    trigger: ".breadcrumb-item:first",
    content: _t("Use the breadcrumbs to <b>go back to products</b>."),
    position: "bottom"
}, {
// Add service product
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_view',
    content: _t('Let\'s create your second product.'),
    position: 'bottom',
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
    trigger: ".o_field_widget[name=taxes_id] input",
    content: _t("Focus on customer taxes field."),
    run: function (actions) {
        actions.click();
        var $e = $('.ui-menu-item:not(.o_m2o_dropdown_option) > a.ui-state-active');
        if ($e.length) {
            actions.click($e);
        } else {
            actions.click(); // close dropdown
        }
    },
}, {
    trigger: '.o_notebook a:contains("Sales")',
    content: _t('Go to sales tab'),
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
    content: _t('Go back to the home menu'),
    position: 'bottom',
}, tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
    content: _t('Organize your sales activities with the <b>CRM app</b>.'),
    position: 'right',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
    content: _t('Organize your sales activities with the <b>CRM app</b>.'),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: ".o-kanban-button-new",
    extra_trigger: '.o_opportunity_kanban',
    content: _t("Click here to <b>create your first opportunity</b> and add it to your pipeline."),
    position: "bottom"
}, {
    trigger: ".o_kanban_quick_create input:first",
    content: _t("<b>Choose a name</b> for your opportunity."),
    position: "right",
    run: "text the_flow.opportunity",
}, {
    trigger: ".o_kanban_quick_create .o_field_widget[name=partner_id] input",
    content: _t("Write the name of your customer to create one on the fly, or select an existing one."),
    position: "left",
    run: "text the_flow.customer",
}, {
    trigger: ".ui-menu-item > a:contains('the_flow.customer')",
    auto: true,
}, {
    trigger: ".o_kanban_quick_create .o_kanban_add",
    extra_trigger: ".o_kanban_quick_create .o_field_widget[name=partner_id] > .o_external_button", // Wait name_create
    content: _t("Click here to <b>add your opportunity</b>."),
    position: "right",
}, {
    trigger: ".o_kanban_group:first .o_kanban_record:has(span:contains('the_flow.opportunity'))",
    content: _t("<b>Drag &amp; drop opportunities</b> between columns as you progress in your sales cycle."),
    position: "right",
    run: "drag_and_drop .o_opportunity_kanban .o_kanban_group:eq(2) ",
}, {
    trigger: ".o_kanban_group:eq(2) > .o_kanban_record:has(span:contains('the_flow.opportunity'))",
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
    /**
     * We need both triggers because the "sale_product_configurator" module replaces the
     * "product_id" field with a "product_template_id" field.
     * This selector will still only ever select one element.
     */
    trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
    content: _t("Select a product, or create a new one on the fly. The product will define the default sales price (that you can change), taxes and description automatically."),
    position: "right",
    run: function (actions) {
        actions.text("the_flow.product", this.$anchor);
        // fake keydown to trigger search
        var keyDownEvent = jQuery.Event("keydown");
        keyDownEvent.which = 42;
        this.$anchor.trigger(keyDownEvent);
        var $descriptionElement = $('.o_form_editable textarea[name="name"]');
        // when description changes, we know the product has been loaded
        $descriptionElement.change(function () {
            if ($(this).val().indexOf('the_flow.product') !== -1){
                $(this).addClass('product_loading_success');
            }
        });
    },
}, {
    trigger: ".ui-menu-item > a:contains('the_flow.product')",
}, {
    trigger: '.o_form_editable textarea[name="name"].product_loading_success',
    run: function () {} // wait for product loading
}, {
    trigger: ".o_field_widget[name=order_line] .o_field_x2many_list_row_add > a",
    content: _t("Click here to add some lines to your quotations."),
    position: "bottom",
}, {
    /**
     * We need both triggers because the "sale_product_configurator" module replaces the
     * "product_id" field with a "product_template_id" field.
     * This selector will still only ever select one element.
     */
    trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
    extra_trigger: '.o_field_widget[name=order_line] .o_data_row:nth(1).o_selected_row',
    content: _t("Select a product"),
    position: "right",
    run: function (actions) {
        actions.text("the_flow.service", this.$anchor);
        // fake keydown to trigger search
        var keyDownEvent = jQuery.Event("keydown");
        keyDownEvent.which = 42;
        this.$anchor.trigger(keyDownEvent);
        var $descriptionElement = $('.o_form_editable textarea[name="name"]');
        // when description changes, we know the product has been loaded
        $descriptionElement.change(function () {
            if ($(this).val().indexOf('the_flow.service') !== -1){
                $(this).addClass('product_service_loading_success');
            }
        });
    },
}, {
    trigger: ".ui-menu-item > a:contains('the_flow.service')",
}, {
    trigger: '.o_form_editable textarea[name="name"].product_service_loading_success',
    run: function () {} // wait for product loading
}, {
    trigger: 'label:contains("Untaxed Amount")',
    // click somewhere else to exit cell focus
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Send by Email')",
    extra_trigger: ".o_statusbar_status .btn-primary:contains('Quotation')",
    content: _t("Try to send it to email"),
    position: "bottom",
}, {
    trigger: ".o_field_widget[name=email]",
    content: _t("Enter an email address"),
    position: "right",
    run: "text test@the_flow.com",
},{
    trigger: ".modal-footer .btn-primary",
    content: _t("Save your changes"),
    position: "bottom",
},  {
    trigger: ".modal-footer .btn-primary span:contains('Send')",
    content: _t("Try to send it to email"),
    position: "bottom",
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Confirm')",
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
    content: _t('Go back to the home menu'),
    position: 'bottom',
}, tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app:contains("Inventory")',
    content: _t('Go to Inventory'),
    position: 'right',
    edition: 'community'
}, {
    trigger: '.o_app > div:contains("Inventory")',
    content: _t('Go to Inventory'),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: ".o_menu_sections a:contains('Master Data')",
    content: _t("Go to Master Data"),
    position: "bottom"
}, {
    trigger: ".o_menu_sections a[data-menu-xmlid='stock.menu_reordering_rules_config']",
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
    trigger: ".o_menu_sections a:contains('Operations')",
    content: _t("Go to Run Schedulers"),
    position: "bottom"
},{
    trigger: ".o_menu_sections a[data-menu-xmlid='stock.menu_procurement_compute']",
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
    content: _t('Go back to the home menu'),
    position: 'bottom',
}, tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app:contains("Purchase")',
    content: _t('Go to Purchase'),
    position: 'right',
    edition: 'community'
}, {
    trigger: '.o_app > div:contains("Purchase")',
    content: _t('Go to Purchase'),
    position: 'bottom',
    edition: 'enterprise'
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
    trigger: ".o_back_button a, .breadcrumb-item:not('.active'):last",
    content: _t('go back to the purchase order'),
    position: 'bottom',
 }, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Create Bill')",
    content: _t('go to Vendor Bills'),
    position: 'bottom',
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Post')",
    content: _t("Try to send it to email"),
    position: "bottom",
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Register Payment')",
    content: _t("Register Payment"),
    position: "bottom",
}, {
    trigger: ".modal-footer .btn-primary",
    content: _t("Validate"),
    position: "bottom",
}, {
    edition: "enterprise",
    trigger: '.o_menu_toggle',
    content: _t('Go back to the home menu'),
    position: 'bottom',
}, tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app:contains("Manufacturing")',
    content: _t('Go to Manufacturing'),
    position: 'right',
    edition: 'community'
}, {
    trigger: '.o_app > div:contains("Manufacturing")',
    content: _t('Go to Manufacturing'),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: ".o_menu_sections a[data-menu-xmlid='mrp.menu_mrp_manufacturing']",
    content: _t('Click on Operations menuitem'),
    position: 'bottom',
}, {
    trigger: ".o_menu_sections a[data-menu-xmlid='mrp.menu_mrp_production_action']",
    content: _t('Open manufacturing orders'),
    position: 'bottom',
}, {
    trigger: '.o_data_row:has(.o_data_cell:contains("the_flow.product")):first',
    content: _t('Select the generated manufacturing order'),
    position: 'bottom',
}, {
    trigger: ".o_statusbar_buttons > button[name='action_assign']:enabled",
    content: _t("Check availability"),
    position: "bottom",
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Produce')",
    content: _t("Produce"),
    position: "bottom",
}, {
    trigger:  ".modal-footer .btn-primary:nth-child(3)",
    content: _t('Record Production'),
    position: 'bottom',
}, {
    trigger: ".o_statusbar_buttons > button:enabled:contains('Mark as Done')",
    content: _t("Mark as Done"),
    position: "bottom",
}, {
    edition: "enterprise",
    trigger: '.o_menu_toggle',
    content: _t('Go back to the home menu'),
    position: 'bottom',
}, tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    content: _t('Organize your sales activities with the <b>Sales app</b>.'),
    position: 'bottom',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    content: _t('Organize your sales activities with the <b>Sales app</b>.'),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: ".o_menu_sections a[data-menu-xmlid='sale.sale_order_menu']",
    content: _t("Go to Sales menu"),
    position: "bottom"
}, {
    trigger: ".o_menu_sections a[data-menu-xmlid='sale.menu_sale_order']",
    content: _t("Go to the sales orders"),
    position: "bottom"
}, {
    trigger: ".o_data_row:first",
    extra_trigger: '.o_control_panel .breadcrumb:contains("Sales Orders")',
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
    trigger: '.breadcrumb-item:nth-child(2) a',
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
    trigger: ".o_statusbar_buttons > button:enabled:contains('Post')",
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
    content: _t('Go back to the home menu'),
    position: 'bottom',
}, {
    edition: "enterprise",
    trigger: '.o_app[data-menu-xmlid="account_accountant.menu_accounting"]',
    content: _t('Go to Accounting'),
    position: 'bottom',
}, {
    edition: "enterprise",
    trigger: 'div[name=bank_journal_cta] > button[data-name=action_cofigure_bank_journal], div[name=bank_journal_cta] > button[data-name=action_configure_bank_journal]',
    content: _t('Configure Bank Journal'),
    position: 'bottom',
}, {
    edition: "enterprise",
    trigger: '.js_configure_manually',
    content: _t('Enter manual data for bank account'),
    position: 'bottom',
}, {
    edition: "enterprise",
    trigger: ".o_field_widget[name=acc_number]",
    content: _t("Enter an account number"),
    position: "right",
    run: "text 867656544",
}, {
    trigger: ".modal-footer .btn-primary",
    content: _t('Save'),
    position: 'bottom',
}, {
    edition: "enterprise",
    trigger: 'div[name=bank_statement_create_button] > a[data-name=create_bank_statement], div[name=bank_statement_create_button] > a[data-name=create_bank_statement]',
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
    in_modal: false,
    auto: true,
}, {
    edition: "enterprise",
    trigger: ".o_selected_row .o_field_widget[name=name]",
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
    trigger: ".button_back_to_statement",
    content: _t('<p><b>Close this statement.</p>'),
    position: "bottom",
}]);
});
