odoo.define('test_main_flows.tour', function (require) {
"use strict";

const {_t} = require('web.core');
const {Markup} = require('web.utils');
const tour = require('web_tour.tour');

tour.register('main_flow_tour', {
    test: true,
    url: "/web",
}, [
...tour.stepUtils.goToAppSteps('sale.sale_menu_root', Markup(_t('Organize your sales activities with the <b>Sales app</b>.'))),
tour.stepUtils.openBuggerMenu("li.breadcrumb-item.active:contains('Quotations')"),
{
// Add Stockable product
    mobile: false,
    trigger: ".o_menu_sections .dropdown-toggle span:contains('Products')",
    extra_trigger: '.o_main_navbar',
    content: _t("Let's create products."),
    position: "bottom",
}, {
    trigger: ".o_menu_sections .dropdown-item:contains('Products'), nav.o_burger_menu_content li[data-menu-xmlid='sale.menu_product_template_action']",
    content: _t("Let's create products."),
    position: "bottom"
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: "li.breadcrumb-item.active:contains('Products')",
    content: _t("Let's create your first product."),
    position: 'bottom',
}, {
    trigger: '.o_field_widget[name=name] input',
    extra_trigger: '.o_form_sheet',
    content: _t("Let's enter the name."),
    position: 'left',
    run: 'text the_flow.product',
}, {
    trigger: ".o_field_widget[name=detailed_type] select",
    content: _t("Let's enter the product type"),
    position: 'left',
    run: 'text "product"',
}, {
    trigger: '.o_notebook .nav-link:contains("Inventory")',
    content: _t('Go to inventory tab'),
    position: 'top',
}, {
    trigger: '.o_field_widget[name=route_ids] .form-check > label:contains("Manufacture")',
    content: _t('Check Manufacture'),
    position: 'right',
}, {
    trigger: '.o_field_widget[name=route_ids] .form-check > label:contains("Buy")',
    content: _t('Uncheck Buy'),
    position: 'right',
}, {
    trigger: '.o_field_widget[name=route_ids] .form-check > label:contains("Replenish on Order (MTO)")',
    content: _t('Uncheck  Replenish on Order (MTO)'),
    position: 'right',
}, {
    trigger: '.o_notebook .nav-link:contains("General Information")',
    content: _t('Go to main tab'),
    position: 'top',
}, {
    mobile: false,
    trigger: ".o_field_widget[name=taxes_id] input",
    content: _t("Focus on customer taxes field."),
    run: function (actions) {
        actions.click();
        const $e = $('.ui-menu-item:not(.o_m2o_dropdown_option) > a.ui-state-active');
        if ($e.length) {
            actions.click($e);
        } else {
            actions.click(); // close dropdown
        }
    },
}, {
    trigger: '.o_form_button_save',
    content: _t("Save this product and the modifications you've made to it."),
    position: 'bottom',
},
tour.stepUtils.autoExpandMoreButtons('.o_form_saved'),
{
    trigger: ".oe_button_box .oe_stat_button div[name=bom_count]",
    extra_trigger: '.o_form_saved',
    content: _t('See Bill of material'),
    position: 'bottom',
}, {
    trigger: ".o_list_button_add",
    content: _t("Let's create a new bill of material"),
    position: "bottom",
}, {
// Add first component
    // FIXME in mobile replace list by kanban + form
    trigger: ".o_field_x2many_list_row_add > a",
    extra_trigger: ".o_form_editable",
    content: _t("Click here to add some lines."),
    position: "bottom",
}, {
    mobile: false,
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: "text the_flow.component1",
}, {
    mobile: false,
    trigger: ".ui-menu-item > a:contains('the_flow.component1')",
    auto: true,
}, {
    mobile: true,
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    content: _t("Click here to open kanban search mobile."),
    position: "bottom",
}, {
    mobile: true,
    trigger: ".modal-dialog .btn:contains('New')",
    extra_trigger: ".modal-dialog",
    content: _t("Click here to add new line."),
    position: "left",
}, {
    mobile: true,
    trigger: '.modal-body .o_form_editable .o_field_widget[name="name"] input',
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: "text the_flow.component1",
}, {
// Edit first component
    mobile: false,
    trigger: ".o_selected_row .o_external_button",
    content: _t("Click here to edit your component"),
    position: "right",
}, {
    trigger: '.o_notebook .nav-link:contains("Inventory")',
    content: _t('Go to inventory tab'),
    position: 'top',
}, {
    // FIXME WOWL: can't toggle boolean by clicking on label (only with tour helpers, only in dialog ???)
    // trigger: '.o_field_widget[name=route_ids] .form-check > label:contains("Replenish on Order (MTO)")',
    trigger: '.o_field_widget[name=route_ids] .form-check:contains("Replenish on Order (MTO)") input',
    content: _t('Check Replenish on Order (MTO)'),
    position: 'right',
}, {
    trigger: '.o_notebook .nav-link:contains("Purchase")',
    content: _t('Go to purchase tab'),
    position: 'top',
}, {
    mobile: false,
    trigger: ".o_field_widget[name=seller_ids] .o_field_x2many_list_row_add > a",
    content: _t("Let's enter the cost price"),
    position: 'right',
}, {
    mobile: false,
    trigger: ".o_field_widget[name=partner_id] input",
    extra_trigger: ".breadcrumb-item.active:contains(the_flow.component1)",
    content: _t('Select a seller'),
    position: 'top',
    run: "text the_flow.vendor",
}, {
    mobile: false,
    trigger: ".ui-menu-item > a:contains('the_flow.vendor')",
    in_modal: false,
}, {
    mobile: true,
    trigger: ".o_field_widget[name=seller_ids] .o-kanban-button-new",
    content: _t("Let's select a vendor"),
    position: 'bottom',
}, {
    mobile: true,
    trigger: ".o_form_editable .o_field_many2one[name=partner_id] input",
    extra_trigger: ".modal:not(.o_inactive_modal) .o_form_editable div:contains('Vendor')",
    content: _t("Select a vendor, or create a new one on the fly."),
    position: "bottom",
}, {
    mobile: true,
    trigger: ".modal-footer .o_create_button",
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Vendor')",
    content: _t("Select a vendor, or create a new one on the fly."),
    position: "right",
}, {
    mobile: true,
    trigger: ".o_field_widget[name=name] input:not(.o_invisible_modifier)",
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-dialog .o_field_radio.o_field_widget[name=company_type]",
    content: _t('Select a seller'),
    position: 'top',
    run: "text the_flow.vendor",
}, {
    mobile: true,
    trigger: '.o_form_button_save',
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Vendor')",
    content: _t("Save this product and the modifications you've made to it."),
    position: 'right',
}, {
    trigger: ".o_field_widget[name=price] input",
    content: _t('Set the cost price'),
    position: 'right',
    run: "text 1",
}, {
    mobile: true,
    trigger: ".modal-footer .btn-primary:contains('Save & Close')",
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Vendor')",
    content: _t('Save & Close'),
    position: 'right',
}, {
    mobile: true,
    trigger: ".modal-footer .btn-primary:contains('Save')",
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Component')",
    content: _t('Save'),
    position: 'right',
}, {
    mobile: true,
    trigger: '.o_field_widget[name=code] input',
    // click somewhere else to exit cell focus
}, {
    mobile: false,
    trigger: 'label:contains("Vendor Taxes")',
    // click somewhere else to exit cell focus
}, {
    mobile: false,
    trigger: '.breadcrumb .o_back_button',
    content: _t('Go back'),
    position: 'bottom',
}, {
// Add second component
    mobile: false,
    trigger: ".o_field_x2many_list_row_add > a",
    extra_trigger: ".breadcrumb-item.active:contains('the_flow.product')",
    content: _t("Click here to add some lines."),
    position: "bottom",
}, {
    mobile: true,
    trigger: ".o_field_x2many_list_row_add > a",
    extra_trigger: ".o_form_editable",
    content: _t("Click here to add some lines."),
    position: "bottom",
}, {
    mobile: true,
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    content: _t("Click here to open kanban search mobile."),
    position: "bottom",
}, {
    mobile: true,
    trigger: ".modal-dialog .btn:contains('New')",
    extra_trigger: ".modal-dialog",
    content: _t("Click here to add new line."),
    position: "left",
}, {
    mobile: true,
    trigger: ".modal-body .o_form_editable .o_field_widget[name=name] input",
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: "text the_flow.component2",
}, {
    mobile: false,
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    extra_trigger: '.o_field_widget[name=bom_line_ids] .o_data_row:nth(1).o_selected_row',
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: "text the_flow.component2",
}, {
    mobile: false,
    trigger: ".ui-menu-item > a:contains('the_flow.component2')",
    auto: true,
}, {
// Edit second component
    mobile: false,
    trigger: ".o_selected_row .o_external_button",
    content: _t("Click here to edit your component"),
    position: "right",
}, {
    trigger: '.o_notebook .nav-link:contains("Purchase")',
    content: _t('Go to purchase tab'),
    position: 'top',
}, {
    mobile: true,
    trigger: ".o_field_widget[name=seller_ids] .o-kanban-button-new",
    content: _t("Let's select a vendor"),
    position: 'bottom',
}, {
    mobile: true,
    trigger: '.o_form_editable .o_field_many2one[name="partner_id"] input',
    extra_trigger: ".modal:not(.o_inactive_modal) .o_form_editable div:contains('Vendor')",
    content: _t("Select a vendor, or create a new one on the fly."),
    position: "bottom",
},
...tour.stepUtils.mobileKanbanSearchMany2X('Vendor', 'the_flow.vendor'),
{
    mobile: false,
    trigger: ".o_field_widget[name=seller_ids] .o_field_x2many_list_row_add > a",
    content: _t("Let's enter the cost price"),
    position: 'right',
}, {
    mobile: false,
    trigger: ".o_field_widget[name=partner_id] input",
    extra_trigger: ".breadcrumb-item.active:contains(the_flow.component2)",
    content: _t('Select a seller'),
    position: 'top',
    run: "text the_flow.vendor",
}, {
    mobile: false,
    trigger: ".ui-menu-item > a:contains('the_flow.vendor')",
    auto: true,
    in_modal: false,
}, {
    trigger: ".o_field_widget[name=price] input",
    extra_trigger: ".o_field_widget[name=partner_id] .o_external_button",
    content: _t('Set the cost price'),
    position: 'right',
    run: "text 1",
}, {
    mobile: true,
    trigger: ".modal-footer .btn-primary:contains('Save & Close')",
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Vendor')",
    content: _t('Save & Close'),
    position: 'right',
}, {
    mobile: true,
    trigger: ".modal-footer .btn-primary:contains('Save')",
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Component')",
    content: _t('Save'),
    position: 'right',
}, {
    mobile: true,
    trigger: '.o_field_widget[name=code] input',
    // click somewhere else to exit cell focus
}, {
    mobile: false,
    trigger: 'label:contains("Vendor Taxes")',
    // click somewhere else to exit cell focus
}, {
    mobile: false,
    trigger: '.breadcrumb .o_back_button',
    content: _t('Go back'),
    position: 'bottom',
}, {
    mobile: false,
    trigger: ".breadcrumb-item:first",
    content: Markup(_t("Use the breadcrumbs to <b>go back to products</b>.")),
    position: "bottom"
},
...tour.stepUtils.goBackBreadcrumbsMobile(
        Markup(_t("Use the breadcrumbs to <b>go back to products</b>.")),
        undefined,
        ".breadcrumb-item.active:contains('Bill of Materials')",
        ".breadcrumb-item.active:contains('the_flow.product')"
    ),
{
// Add service product
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_view',
    content: _t("Let's create your second product."),
    position: 'bottom',
}, {
    trigger: '.o_field_widget[name=name] input',
    extra_trigger: '.o_form_sheet',
    content: _t("Let's enter the name."),
    position: 'left',
    run: 'text the_flow.service',
}, {
    trigger: '.o_field_widget[name=detailed_type] select',
    content: _t('Set to service'),
    position: 'left',
    run: 'text "service"',
}, {
    mobile: false,
    trigger: ".o_field_widget[name=taxes_id] input",
    content: _t("Focus on customer taxes field."),
    run: function (actions) {
        actions.click();
        const $e = $('.o_field_widget[name=taxes_id] .o-autocomplete--dropdown-item:not(.o_m2o_dropdown_option) > a');
        if ($e.length) {
            actions.click($e);
        } else {
            actions.click(); // close dropdown
        }
    },
}, {
    trigger: '.o_field_widget[name=service_policy] select',
    content: _t('Change service policy'),
    position: 'left',
    run: 'text "delivered_timesheet"',
}, {
    trigger: '.o_field_widget[name=service_tracking] select',
    content: _t('Change track service'),
    position: 'left',
    run: 'text "task_global_project"',
}, {
    mobile: false,
    trigger: '.o_field_widget[name=project_id] input',
    content: _t('Choose project'),
    position: 'left',
    run: 'text the_flow.project',
}, {
    mobile: true,
    trigger: '.o_field_widget[name=project_id] input',
    content: _t('Choose project'),
    position: 'left',
}, {
    mobile: true,
    trigger: ".modal-dialog .btn:contains('New')",
    extra_trigger: ".modal-dialog",
    content: _t("Click here to add new line."),
    position: "left",
}, {
    mobile: true,
    trigger: '.o_field_widget[name=name] input',
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Project')",
    content: _t('Let\'s enter the name.'),
    position: 'left',
    run: 'text the_flow.project',
}, {
    mobile: false,
    trigger: ".o-autocomplete--dropdown-item > a:contains('the_flow.project')",
    auto: true,
}, {
    mobile: true,
    trigger: ".modal-footer .btn-primary:contains('Save')",
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Project')",
    content: _t('Save'),
    position: 'right',
}, {
    trigger: '.o_form_button_save',
    content: _t("Save this product and the modifications you've made to it."),
    position: 'bottom',
}, {
// Create an opportunity
    edition: "enterprise",
    trigger: '.o_menu_toggle',
    content: _t('Go back to the home menu'),
    position: 'bottom',
},
...tour.stepUtils.goToAppSteps('crm.crm_menu_root', Markup(_t('Organize your sales activities with the <b>CRM app</b>.'))),
{
    trigger: ".o-kanban-button-new",
    extra_trigger: '.o_opportunity_kanban',
    content: Markup(_t("Click here to <b>create your first opportunity</b> and add it to your pipeline.")),
    position: "bottom"
}, {
    trigger: ".o_kanban_quick_create .o_field_widget[name=name] input",
    content: Markup(_t("<b>Choose a name</b> for your opportunity.")),
    position: "right",
    run: "text the_flow.opportunity",
}, {
    mobile: false,
    trigger: ".o_kanban_quick_create .o_field_widget[name=partner_id] input",
    content: _t("Write the name of your customer to create one on the fly, or select an existing one."),
    position: "left",
    run: "text the_flow.customer",
}, {
    mobile: true,
    trigger: ".o_kanban_quick_create .o_field_widget[name=partner_id] input",
    content: _t("Write the name of your customer to create one on the fly, or select an existing one."),
    position: "left",
}, {
    mobile: true,
    trigger: ".modal-dialog .btn:contains('New')",
    extra_trigger: ".modal-dialog",
    content: _t("Click here to add new line."),
    position: "left",
}, {
    mobile: true,
    trigger: ".o_field_widget[name=name] input:not(.o_invisible_modifier)",
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Organization / Contact')",
    content: _t('Let\'s enter the name.'),
    position: 'left',
    run: 'text the_flow.customer',
}, {
    mobile: false,
    trigger: ".ui-menu-item > a:contains('the_flow.customer')",
    auto: true,
}, {
    mobile: true,
    trigger: ".modal-footer .btn-primary:contains('Save')",
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Organization / Contact')",
    content: _t('Save'),
    position: 'right',
}, {
    trigger: ".o_kanban_quick_create .o_kanban_add",
    extra_trigger: ".o_kanban_quick_create .o_field_widget[name=partner_id] .o_external_button", // Wait name_create
    content: Markup(_t("Click here to <b>add your opportunity</b>.")),
    position: "right",
}, {
    mobile: false,
    trigger: ".o_kanban_group:first .o_kanban_record span:contains('the_flow.opportunity')",
    content: Markup(_t("<b>Drag &amp; drop opportunities</b> between columns as you progress in your sales cycle.")),
    position: "right",
    run: "drag_and_drop_native .o_opportunity_kanban .o_kanban_group:eq(2) ",
}, {
    mobile: false,
    trigger: ".o_kanban_group:eq(2) > .o_kanban_record span:contains('the_flow.opportunity')",
    content: _t("Click on an opportunity to zoom to it."),
    position: "bottom",
}, {
    mobile: true,
    trigger: ".o_kanban_group:first .o_kanban_record span:contains('the_flow.opportunity')",
    content: _t("Open the_flow.opportunity"),
    position: "bottom",
}, {
    mobile: true,
    trigger: ".o_statusbar_status .btn.dropdown-toggle",
    content: _t("Change status from New to proposition."),
    position: "bottom",
}, {
    mobile: true,
    trigger: ".o_statusbar_status .btn:contains(Proposition)",
    content: _t("Change status from New to proposition."),
    position: "bottom",
},
// Create a quotation
...tour.stepUtils.statusbarButtonsSteps('New Quotation', Markup(_t('<p><b>Create a quotation</p>'))),
{
    mobile: false,
    trigger: ".o_field_widget[name=order_line] .o_field_x2many_list_row_add > a",
    content: _t("Click here to add some lines to your quotations."),
    position: "bottom",
}, {
    mobile: true,
    trigger: ".o_field_widget[name=order_line] .btn:contains(Add)",
    content: _t("Click here to add some lines to your quotations."),
    position: "bottom",
}, {
    /**
     * We need both triggers because the "sale_product_configurator" module replaces the
     * "product_id" field with a "product_template_id" field.
     * This selector will still only ever select one element.
     */
    mobile: false,
    trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
    content: _t("Select a product, or create a new one on the fly. The product will define the default sales price (that you can change), taxes and description automatically."),
    position: "right",
    run: "text the_flow.product",
}, {
    mobile: false,
    trigger: ".ui-menu-item > a:contains('the_flow.product')",
}, {
    mobile: false,
    trigger: "td[name='name'][data-tooltip*='the_flow.product']",
    run: () => {}, // check
}, {
    mobile: true,
    trigger: ".o_field_widget[name=product_id] input",
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Order Lines')",
    content: _t("Select a product, or create a new one on the fly. The product will define the default sales price (that you can change), taxes and description automatically."),
    position: "right",
},
...tour.stepUtils.mobileKanbanSearchMany2X('Product', 'the_flow.product'),
{
    mobile: false,
    trigger: ".o_field_widget[name=order_line] .o_field_x2many_list_row_add > a",
    content: _t("Click here to add some lines to your quotations."),
    position: "bottom",
}, {
    mobile: true,
    trigger: ".modal-footer .btn-primary:contains('Save & New')",
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Order Lines')",
    content: _t('Save & New'),
    position: 'right',
}, {
    /**
     * We need both triggers because the "sale_product_configurator" module replaces the
     * "product_id" field with a "product_template_id" field.
     * This selector will still only ever select one element.
     */
    mobile: false,
    trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
    extra_trigger: '.o_field_widget[name=order_line] .o_data_row:nth(1).o_selected_row',
    content: _t("Select a product"),
    position: "right",
    run: "text the_flow.service",
}, {
    mobile: false,
    trigger: ".ui-menu-item > a:contains('the_flow.service')",
}, {
    mobile: false,
    trigger: "td[name='name'][data-tooltip*='the_flow.service']",
    run: () => {}, // check
}, {
    mobile: false,
    trigger: 'label:contains("Untaxed Amount")',
    // click somewhere else to exit cell focus
}, {
    mobile: true,
    trigger: ".o_field_widget[name=product_id] input",
    extra_trigger: '.o_field_widget[name=order_line] .oe_kanban_card:contains(the_flow.product)',
    content: _t("Select a product, or create a new one on the fly. The product will define the default sales price (that you can change), taxes and description automatically."),
    position: "right",
},
...tour.stepUtils.mobileKanbanSearchMany2X('Product', 'the_flow.service'),
{
    mobile: true,
    trigger: ".modal-footer .btn-primary:contains('Save & Close')",
    extra_trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Order Lines')",
    content: _t('Save & Close'),
    position: 'right',
},
...tour.stepUtils.statusbarButtonsSteps('Send by Email', _t("Try to send it to email"), ".o_statusbar_status .btn:contains('Quotation')"),
{
    trigger: ".o_field_widget[name=email] input",
    content: _t("Enter an email address"),
    position: "right",
    run: "text test@the_flow.com",
}, {
    trigger: ".modal-footer .btn-primary",
    content: _t("Save your changes"),
    position: "bottom",
}, {
    trigger: ".modal-footer .btn-primary:contains('Send')",
    content: _t("Try to send it to email"),
    position: "bottom",
},
...tour.stepUtils.statusbarButtonsSteps('Confirm', Markup(_t("<p>Confirm this quotation</p>"))),
{
    edition: "enterprise",
    trigger: '.o_menu_toggle',
    content: _t('Go back to the home menu'),
    position: 'bottom',
},
...tour.stepUtils.goToAppSteps('stock.menu_stock_root', _t('Go to Inventory')),
tour.stepUtils.openBuggerMenu("li.breadcrumb-item.active:contains('Inventory Overview')"),
{
    mobile: false,
    trigger: ".o_menu_sections button[data-menu-xmlid='stock.menu_stock_config_settings']",
    extra_trigger: '.o_main_navbar',
    content: _t("Go to Configuration"),
    position: "bottom"
}, {
    trigger: ".o_menu_sections .dropdown-item[data-menu-xmlid='stock.menu_reordering_rules_config'], nav.o_burger_menu_content li[data-menu-xmlid='stock.menu_reordering_rules_config']",
    content: _t("Reordering Rules"),
    position: "bottom"
}, {
    mobile: false,
    trigger: ".o_list_button_add",
    content: _t("Let's create a new reordering rule"),
    position: "right",
}, {
    mobile: true,
    trigger: ".o-kanban-button-new",
    content: _t("Let's create a new reordering rule"),
    position: "right",
}, {
    mobile: false,
    trigger: ".o_field_widget[name=product_id] input",
    content: _t("Write the name of your product."),
    position: "top",
    run: "text the_flow.component2",
}, {
    mobile: false,
    trigger: ".ui-menu-item > a:contains('the_flow.component2')",
    auto: true,
}, {
    mobile: true,
    trigger: ".o_field_widget[name=product_id] input",
    content: _t("Write the name of your product."),
    position: "top",
},
...tour.stepUtils.mobileKanbanSearchMany2X('Product', 'the_flow.component2'),
{
    // FIXME WOWL: remove first part of selector when legacy view is dropped
    trigger: "input.o_field_widget[name=product_min_qty], .o_field_widget[name=product_min_qty] input",
    content: _t("Set the minimum product quantity"),
    position: "right",
    run: 'text 1',
}, {
    // FIXME WOWL: remove first part of selector when legacy view is dropped
    trigger: "input.o_field_widget[name=product_max_qty], .o_field_widget[name=product_max_qty] input",
    content: _t("Set the maximum product quantity"),
    position: "right",
    run: 'text 10',
}, {
    mobile: false,
    trigger: ".o_list_button_save",
    content: Markup(_t("<p>Save this reordering rule</p>")),
    position: "bottom"
}, {
    mobile: true,
    trigger: ".o_form_button_save",
    content: Markup(_t("<p>Save this reordering rule</p>")),
    position: "bottom"
},
tour.stepUtils.openBuggerMenu("li.breadcrumb-item.active:contains('OP/')"),
{
//Go to purchase:
    edition: "enterprise",
    trigger: '.o_menu_toggle',
    content: _t('Go back to the home menu'),
    position: 'bottom',
},
...tour.stepUtils.goToAppSteps('purchase.menu_purchase_root', _t('Go to Purchase')),
{
    mobile: false,
    trigger: '.o_data_row:has(.o_data_cell:contains("the_flow.vendor")) .o_data_cell:first',
    content: _t('Select the generated request for quotation'),
    position: 'bottom',
}, {
    mobile: true,
    trigger: '.o_kanban_record .o_kanban_record_title:contains("the_flow.vendor")',
    content: _t('Select the generated request for quotation'),
    position: 'bottom',
},
...tour.stepUtils.statusbarButtonsSteps('Confirm Order', _t("Confirm quotation")),
...tour.stepUtils.statusbarButtonsSteps('Receive Products', _t("Receive Product"), ".o_statusbar_status .btn.dropdown-toggle:contains('Purchase Order')"),
...tour.stepUtils.statusbarButtonsSteps('Validate', _t("Validate"), ".o_statusbar_status .btn.dropdown-toggle:contains('Ready')"),
{
    trigger: ".modal-footer .btn-primary",
    extra_trigger: ".modal-dialog",
    content: _t("Apply"),
    position: "bottom",
}, {
    trigger: ".o_back_button a, .breadcrumb-item:not('.active'):last",
    content: _t('go back to the purchase order'),
    position: 'bottom',
},
...tour.stepUtils.statusbarButtonsSteps('Create Bill', _t('go to Vendor Bills'), ".o_statusbar_status .btn.dropdown-toggle:contains('Purchase Order')"),
{
    trigger:".o_field_widget[name=invoice_date] input",
    extra_trigger: ".o_form_label .o_field_widget:contains('Vendor Bill')",
    content: _t('Set the invoice date'),
    run: "text 01/01/2020",
},
...tour.stepUtils.statusbarButtonsSteps('Confirm', _t("Try to send it to email"), ".o_statusbar_status .btn.dropdown-toggle:contains('Draft')"),
...tour.stepUtils.statusbarButtonsSteps('Register Payment', _t("Register Payment"), ".o_statusbar_status .btn.dropdown-toggle:contains('Posted')"),
{
    trigger: ".modal-footer .btn-primary",
    content: _t("Validate"),
    position: "bottom",
}, {
    edition: "enterprise",
    trigger: '.o_menu_toggle',
    content: _t('Go back to the home menu'),
    position: 'bottom',
},
...tour.stepUtils.goToAppSteps('mrp.menu_mrp_root', _t('Go to Manufacturing')),
tour.stepUtils.openBuggerMenu("li.breadcrumb-item.active:contains('Manufacturing Orders'), li.breadcrumb-item.active:contains('Work Centers Overview')"),
{
    mobile: false,
    trigger: ".o_menu_sections button[data-menu-xmlid='mrp.menu_mrp_manufacturing']",
    content: _t('Click on Operations menuitem'),
    position: 'bottom',
}, {
    trigger: ".o_menu_sections .dropdown-item[data-menu-xmlid='mrp.menu_mrp_production_action'], nav.o_burger_menu_content li[data-menu-xmlid='mrp.menu_mrp_production_action']",
    content: _t('Open manufacturing orders'),
    position: 'bottom',
}, {
    mobile: false,
    trigger: '.o_data_row:has(.o_data_cell:contains("the_flow.product")):first .o_data_cell:first',
    content: _t('Select the generated manufacturing order'),
    position: 'bottom',
}, {
    mobile: true,
    trigger: '.o_kanban_record .o_kanban_record_title:contains("the_flow.product"):first',
    extra_trigger: "li.breadcrumb-item.active:contains('Manufacturing Orders')",
    content: _t('Select the generated manufacturing order'),
    position: 'bottom',
},
...tour.stepUtils.statusbarButtonsSteps('Unreserve', _t("Unreserve")),
{
    trigger: ".o_field_widget[name=qty_producing] input",
    extra_trigger: ".o_field_widget[name=move_raw_ids] tr[data-id]:first .o_field_widget[name=forecast_availability]:contains('Available')",
    position: 'left',
    content: _t("Produce"),
    run: "text 1",
},
...tour.stepUtils.statusbarButtonsSteps('Check availability', _t("Check availability")),
{
    trigger: ".o_field_widget[name=qty_producing] input",
    extra_trigger: ".o_field_widget[name=move_raw_ids] tr[data-id]:first .o_field_widget[name=forecast_availability]:contains('1')",
    position: 'left',
    content: _t("Produce"),
    run: "text 1",
},

...tour.stepUtils.statusbarButtonsSteps('Mark as Done', _t("Mark as Done"), ".o_statusbar_status .btn.dropdown-toggle:contains('To Close')"),
{
    edition: "enterprise",
    trigger: '.o_menu_toggle',
    content: _t('Go back to the home menu'),
    position: 'bottom',
},
...tour.stepUtils.goToAppSteps('sale.sale_menu_root', Markup(_t('Organize your sales activities with the <b>Sales app</b>.'))),
tour.stepUtils.openBuggerMenu("li.breadcrumb-item.active:contains('Quotations')"),
{
    mobile: false,
    trigger: ".o_menu_sections button[data-menu-xmlid='sale.sale_order_menu']",
    content: _t("Go to Sales menu"),
    position: "bottom"
}, {
    trigger: ".o_menu_sections .dropdown-item[data-menu-xmlid='sale.menu_sale_order'], nav.o_burger_menu_content li[data-menu-xmlid='sale.menu_sale_order']",
    content: _t("Go to the sales orders"),
    position: "bottom"
}, {
    mobile: false,
    trigger: ".o_data_cell:contains('the_flow.customer')",
    extra_trigger: '.o_control_panel .breadcrumb:contains("Sales Orders")',
    content: _t("Go to the last sale order"),
    position: "right"
}, {
    mobile: true,
    trigger: ".o_kanban_record .o_kanban_record_title:contains('the_flow.customer')",
    extra_trigger: '.o_control_panel .breadcrumb:contains("Sales Orders")',
    content: _t("Go to the last sale order"),
    position: "bottom"
},
tour.stepUtils.mobileModifier(tour.stepUtils.autoExpandMoreButtons('.o_control_panel .breadcrumb:contains("S0")')),
{
    mobile: false,
    trigger: '.oe_button_box .oe_stat_button:has(div[name=tasks_count])',
    content: _t('See Tasks'),
    position: 'right',
}, {
    mobile: true,
    trigger: '.oe_button_box .oe_stat_button:has(div[name=tasks_count])',
    extra_trigger: '.o_control_panel .breadcrumb:contains("S0")',
    content: _t('See Tasks'),
    position: 'bottom',
}, {
    trigger: 'a.nav-link:contains(Timesheets)',
    extra_trigger: 'div.o_notebook_headers',
    content: 'Click on Timesheets page to log a timesheet',
}, {
    mobile: false,
    trigger: 'div[name="timesheet_ids"] td.o_field_x2many_list_row_add a[role="button"]',
    content: 'Click on Add a line to create a new timesheet into the task.',
}, {
    mobile: true,
    trigger: '.o-kanban-button-new',
    content: _t('Open the full search field'),
    position: 'bottom',
}, {
    mobile: false,
    trigger: 'div[name="timesheet_ids"] div[name="name"] input',
    content: 'Enter a description this timesheet',
    run: 'text 10 hours',
}, {
    mobile: true,
    trigger: '.modal-content.o_form_view div[name="name"] input',
    content: 'Enter a description this timesheet',
    run: 'text 10 hours',
}, {
    mobile: false,
    trigger: 'div[name="timesheet_ids"] div[name="unit_amount"] input',
    content: 'Enter one hour for this timesheet',
    run: 'text 10',
}, {
    mobile: true,
    trigger: '.modal-content.o_form_view div[name="unit_amount"] input',
    content: 'Enter one hour for this timesheet',
    run: 'text 10',
}, {
    content: "save",
    trigger: ".o_form_button_save",
},
...tour.stepUtils.goBackBreadcrumbsMobile(
        _t('Back to the sale order'),
        undefined,
        ".breadcrumb-item.active:contains('the_flow.service')"
    ),
{
    mobile: false,
    trigger: '.breadcrumb-item:nth-child(2) a',
    extra_trigger: 'div:not(".o_form_editable")', // Waiting save
    content: _t('Back to the sale order'),
    position: 'bottom',
},
...tour.stepUtils.statusbarButtonsSteps('Create Invoice', _t("Validate"), ".o_field_widget[name=order_line]"),
{
    trigger: ".modal-footer .btn-primary",
    content: _t("Create and View Invoices"),
    position: "bottom",
},
...tour.stepUtils.statusbarButtonsSteps('Confirm', _t("Validate"), ".breadcrumb-item.active:contains('Draft Invoice')"),
...tour.stepUtils.statusbarButtonsSteps('Register Payment', _t("Register Payment"), ".o_statusbar_status .btn.dropdown-toggle:contains('Posted')"),
{
    trigger: ".modal-footer .btn-primary",
    content: _t("Validate"),
    position: "bottom",
}, {
    edition: "community",
    content: "wait for payment registration to succeed",
    trigger: "span.bg-success:contains('Paid')",
    auto: true,
    run() {}
},{
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
    mobile: false,
    edition: "enterprise",
    trigger: "div.o_account_kanban div.o_kanban_card_header a.oe_kanban_action span:contains('Bank')",
    content: _t("Open the bank reconciliation widget"),
}, {
    mobile: false,
    edition: "enterprise",
    trigger: "button.o_switch_view.o_list",
    content: _t("Move back to the list view"),
}, {
    mobile: false,
    edition: "enterprise",
    trigger: "button.o_list_button_add",
    content: _t("Create a new bank transaction"),
}, {
    mobile: false,
    edition: "enterprise",
    trigger: '.o_field_widget[name=amount] input',
    content: _t("Write the amount received."),
    position: "bottom",
    run: "text 11.00",
}, {
    mobile: false,
    edition: "enterprise",
    trigger: ".o_selected_row .o_field_widget[name=payment_ref] input",
    content: _t("Let's enter a name."),
    run: "text the_flow.statement.line",
}, {
    mobile: false,
    edition: "enterprise",
    trigger: ".o_selected_row .o_field_widget[name=partner_id] input",
    content: _t("Write the name of your customer."),
    position: "bottom",
    run: "text the_flow.customer",
}, {
    mobile: false,
    edition: "enterprise",
    trigger: ".ui-menu-item > a:contains('the_flow.customer')",
    in_modal: false,
    auto: true,
}, {
    mobile: false,
    edition: "enterprise",
    trigger: '.o_list_button_save',
    extra_trigger: ".o_selected_row .o_field_widget[name=partner_id] .o_external_button",
    content: _t('Save.'),
    position: 'bottom',
}, {
    mobile: false,
    edition: "enterprise",
    trigger: "button.o_switch_view.o_kanban",
    extra_trigger: ".o_list_button_add",
    content: _t("Move back to the kanban view"),
}, {
    mobile: false,
    edition: "enterprise",
    trigger: "div.o_bank_rec_st_line_kanban_card span:contains('the_flow.customer')",
    extra_trigger: "div.o_bank_rec_st_line_kanban_card span:contains('the_flow.customer')",
    content: _t("Select the newly created bank transaction"),
}, {
    mobile: false,
    edition: "enterprise",
    trigger: "button[name='button_validate'].btn-primary",
    extra_trigger: "button[name='button_validate'].btn-primary",
    content: _t("Reconcile the bank transaction"),
},
// exit reconciliation widget
{
    ...tour.stepUtils.toggleHomeMenu(),
    mobile: false,
    auto: true,
},
{
    trigger: `.o_app[data-menu-xmlid="account_accountant.menu_accounting"]`,
    edition: 'enterprise',
    mobile: false,
    auto: true,
},
{
    mobile: false,
    edition: "enterprise",
    content: "check that we're back on the dashboard",
    trigger: 'a:contains("Customer Invoices")',
    auto: true,
    run() {}
}]);
});
