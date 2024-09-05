/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";
import { queryFirst } from "@odoo/hoot-dom";

registry.category("web_tour.tours").add('main_flow_tour', {
    test: true,
    url: "/web",
    steps: () => [
...stepUtils.goToAppSteps('sale.sale_menu_root', markup(_t('Organize your sales activities with the <b>Sales app</b>.'))),
{
    isActive: ["mobile"],
    trigger: ".o_breadcrumb .active:contains('Quotations')",
},
{
    isActive: ["mobile"],
    trigger: ".o_mobile_menu_toggle",
    content: _t("Open bugger menu."),
    position: "bottom",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_main_navbar",
},
{
// Add Stockable product
    isActive: ["desktop"],
    trigger: ".o_menu_sections .dropdown-toggle span:contains('Products')",
    content: _t("Let's create products."),
    position: "bottom",
    run: "click",
}, {
    trigger: ".dropdown-item:contains('Products'), nav.o_burger_menu_content li[data-menu-xmlid='sale.menu_product_template_action']",
    content: _t("Let's create products."),
    position: "bottom",
    run: "click",
},
{
    trigger: ".o_breadcrumb .active:contains('Products')",
},
{
    trigger: '.o-kanban-button-new',
    content: _t("Let's create your first product."),
    position: 'bottom',
    run: "click",
},
{
    trigger: '.o_form_sheet',
},
{
    trigger: '.o_field_widget[name=name] textarea',
    content: _t("Let's enter the name."),
    position: 'left',
    run: "edit the_flow.product",
}, {
    trigger: ".o_field_widget[name=is_storable] input",
    content: _t("Let's enter the product type"),
    position: 'right',
    run: "click",
}, {
    trigger: '.o_notebook .nav-link:contains("Inventory")',
    content: _t('Go to inventory tab'),
    position: 'top',
    run: "click",
}, {
    trigger: '.o_field_widget[name=route_ids] .form-check > label:contains("Manufacture")',
    content: _t('Check Manufacture'),
    position: 'right',
    run: "click",
}, {
    trigger: '.o_field_widget[name=route_ids] .form-check > label:contains("Buy")',
    content: _t('Uncheck Buy'),
    position: 'right',
    run: "click",
}, {
    trigger: '.o_field_widget[name=route_ids] .form-check > label:contains("Replenish on Order (MTO)")',
    content: _t('Uncheck  Replenish on Order (MTO)'),
    position: 'right',
    run: "click",
}, {
    trigger: '.o_notebook .nav-link:contains("General Information")',
    content: _t('Go to main tab'),
    position: 'top',
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=taxes_id] input",
    content: _t("Focus on customer taxes field."),
    async run(actions) {
        await actions.click();
        const e = queryFirst(".ui-menu-item:not(.o_m2o_dropdown_option) > a.ui-state-active");
        if (e) {
            await actions.click(e);
        } else {
            await actions.click(); // close dropdown
        }
    },
}, {
    trigger: '.o_form_button_save',
    content: _t("Save this product and the modifications you've made to it."),
    position: 'bottom',
    run: "click",
},
{
    trigger: ".o_form_saved",
},
stepUtils.autoExpandMoreButtons(),
{
    trigger: '.o_form_saved',
},
{
    trigger: ".oe_stat_button div[name=bom_count]",
    content: _t('See Bill of material'),
    position: 'bottom',
    run: "click",
}, {
    trigger: ".o_list_button_add",
    content: _t("Let's create a new bill of material"),
    position: "bottom",
    run: "click",
},
{
    trigger: ".o_form_editable",
},
{
// Add first component
    // FIXME in mobile replace list by kanban + form
    trigger: ".o_field_x2many_list_row_add > a",
    content: _t("Click here to add some lines."),
    position: "bottom",
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: "edit the_flow.component1",
}, {
    isActive: ["auto", "desktop"],
    trigger: ".ui-menu-item > a:contains('the_flow.component1')",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    content: _t("Click here to open kanban search mobile."),
    position: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".modal-dialog .btn:contains('New')",
    content: _t("Click here to add new line."),
    position: "left",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: '.modal-body .o_form_editable .o_field_widget[name="name"] textarea',
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: "edit the_flow.component1",
}, {
// Edit first component
    isActive: ["desktop"],
    trigger: ".o_selected_row .o_external_button",
    content: _t("Click here to edit your component"),
    position: "right",
    run: "click",
}, {
    trigger: '.o_notebook .nav-link:contains("Inventory")',
    content: _t('Go to inventory tab'),
    position: 'top',
    run: "click",
}, {
    // FIXME WOWL: can't toggle boolean by clicking on label (only with tour helpers, only in dialog ???)
    // trigger: '.o_field_widget[name=route_ids] .form-check > label:contains("Replenish on Order (MTO)")',
    trigger: '.o_field_widget[name=route_ids] .form-check:contains("Replenish on Order (MTO)") input',
    content: _t('Check Replenish on Order (MTO)'),
    position: 'right',
    run: "click",
}, {
    trigger: '.o_notebook .nav-link:contains("Purchase")',
    content: _t('Go to purchase tab'),
    position: 'top',
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=seller_ids] .o_field_x2many_list_row_add > a",
    content: _t("Let's enter the cost price"),
    position: 'right',
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_breadcrumb .active:contains(the_flow.component1)",
},
{
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=partner_id] input",
    content: _t('Select a seller'),
    position: 'top',
    run: "edit the_flow.vendor",
}, {
    isActive: ["desktop"],
    trigger: ".ui-menu-item > a:contains('the_flow.vendor')",
    in_modal: false,
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=seller_ids] .o-kanban-button-new",
    content: _t("Let's select a vendor"),
    position: 'bottom',
    run: "click",
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .o_form_editable div:contains('Vendor')",
},
{
    isActive: ["mobile"],
    trigger: ".o_form_editable .o_field_many2one[name=partner_id] input",
    content: _t("Select a vendor, or create a new one on the fly."),
    position: "bottom",
    run: "click",
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Vendor')",
},
{
    isActive: ["mobile"],
    trigger: ".modal-footer .o_create_button",
    content: _t("Select a vendor, or create a new one on the fly."),
    position: "right",
    run: "click",
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-dialog .o_field_radio.o_field_widget[name=company_type]",
},
{
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=name] input:not(.o_invisible_modifier)",
    content: _t('Select a seller'),
    position: 'top',
    run: "edit the_flow.vendor",
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Vendor')",
},
{
    isActive: ["mobile"],
    trigger: '.o_form_button_save',
    content: _t("Save this product and the modifications you've made to it."),
    position: 'right',
    run: "click",
}, {
    trigger: ".o_field_widget[name=price] input",
    content: _t('Set the cost price'),
    position: 'right',
    run: "edit 1",
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Vendor')",
},
{
    isActive: ["mobile"],
    trigger: ".modal-footer .btn-primary:contains('Save & Close')",
    content: _t('Save & Close'),
    position: 'right',
    run: "click",
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Component')",
},
{
    isActive: ["mobile"],
    trigger: ".modal-footer .btn-primary:contains('Save')",
    content: _t('Save'),
    position: 'right',
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: '.o_field_widget[name=code] input',
    run: "edit Test",
    // click somewhere else to exit cell focus
}, {
    isActive: ["desktop"],
    trigger: 'label:contains("Purchase Unit")',
    run: "click",
    // click somewhere else to exit cell focus
}, {
    isActive: ["desktop"],
    trigger: '.breadcrumb .o_back_button',
    content: _t('Go back'),
    position: 'bottom',
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_breadcrumb .active:contains('the_flow.product')",
},
{
// Add second component
    isActive: ["desktop"],
    trigger: ".o_field_x2many_list_row_add > a",
    content: _t("Click here to add some lines."),
    position: "bottom",
    run: "click",
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: ".o_form_editable",
},
{
    isActive: ["mobile"],
    trigger: ".o_field_x2many_list_row_add > a",
    content: _t("Click here to add some lines."),
    position: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    content: _t("Click here to open kanban search mobile."),
    position: "bottom",
    run: "click",
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal-dialog",
},
{
    isActive: ["mobile"],
    trigger: ".modal-dialog .btn:contains('New')",
    content: _t("Click here to add new line."),
    position: "left",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".modal-body .o_form_editable .o_field_widget[name=name] textarea",
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: "edit the_flow.component2",
},
{
    isActive: ["desktop"],
    trigger: '.o_field_widget[name=bom_line_ids] .o_data_row:nth-child(2).o_selected_row',
},
{
    isActive: ["desktop"],
    trigger: ".o_selected_row .o_required_modifier[name=product_id] input",
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: "edit the_flow.component2",
}, {
    isActive: ["auto", "desktop"],
    trigger: ".ui-menu-item > a:contains('the_flow.component2')",
    run: "click",
}, {
// Edit second component
    isActive: ["desktop"],
    trigger: ".o_selected_row .o_external_button",
    content: _t("Click here to edit your component"),
    position: "right",
    run: "click",
}, {
    trigger: '.o_notebook .nav-link:contains("Purchase")',
    content: _t('Go to purchase tab'),
    position: 'top',
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=seller_ids] .o-kanban-button-new",
    content: _t("Let's select a vendor"),
    position: 'bottom',
    run: "click",
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .o_form_editable div:contains('Vendor')",
},
{
    isActive: ["mobile"],
    trigger: '.o_form_editable .o_field_many2one[name="partner_id"] input',
    content: _t("Select a vendor, or create a new one on the fly."),
    position: "bottom",
    run: "click",
},
...stepUtils.mobileKanbanSearchMany2X('Vendor', 'the_flow.vendor'),
{
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=seller_ids] .o_field_x2many_list_row_add > a",
    content: _t("Let's enter the cost price"),
    position: 'right',
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_breadcrumb .active:contains(the_flow.component2)",
},
{
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=partner_id] input",
    content: _t('Select a seller'),
    position: 'top',
    run: "edit the_flow.vendor",
}, {
    isActive: ["auto", "desktop"],
    trigger: ".ui-menu-item > a:contains('the_flow.vendor')",
    in_modal: false,
    run: "click",
},
{
    trigger: ".o_field_widget[name=partner_id] .o_external_button",
},
{
    trigger: ".o_field_widget[name=price] input",
    content: _t('Set the cost price'),
    position: 'right',
    run: "edit 1",
},
{
     in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Vendor')",
},
{
    isActive: ["mobile"],
    trigger: ".modal-footer .btn-primary:contains('Save & Close')",
    content: _t('Save & Close'),
    position: 'right',
    run: "click",
},
{
     in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Component')",
},
{
    isActive: ["mobile"],
    trigger: ".modal-footer .btn-primary:contains('Save')",
    content: _t('Save'),
    position: 'right',
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: '.o_field_widget[name=code] input',
    run: "edit Test",
    // click somewhere else to exit cell focus
}, {
    isActive: ["desktop"],
    trigger: 'label:contains("Purchase Unit")',
    run: "click",
    // click somewhere else to exit cell focus
}, {
    trigger: '.o_back_button',
    content: _t('Go back'),
    position: 'bottom',
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_breadcrumb .active:contains('the_flow.product')",
},
{
    isActive: ["desktop"],
    trigger: '.breadcrumb .o_back_button',
    content: _t('Go back'),
    position: 'bottom',
    run: "click",
},
{
    trigger: ".o_breadcrumb .active:contains('Bill of Materials')",
},
{
    trigger: '.o_back_button',
    content: _t('Go back'),
    position: 'bottom',
    run: "click",
},
{
    trigger: ".o_breadcrumb .active:contains('the_flow.product')",
},
{
    trigger: '.o_back_button',
    content: _t('Go back'),
    position: 'bottom',
    run: "click",
},
{
    trigger: '.o_kanban_view',
},
{
// Add service product
    trigger: '.o-kanban-button-new',
    content: _t("Let's create your second product."),
    position: 'bottom',
    run: "click",
},
{
    trigger: '.o_form_sheet',
},
{
    trigger: '.o_field_widget[name=name] textarea',
    content: _t("Let's enter the name."),
    position: 'left',
    run: "edit the_flow.service",
}, {
    trigger: '.o_field_widget[name="type"] input[data-value="service"]',
    content: _t('Set to service'),
    position: 'left',
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=taxes_id] input",
    content: _t("Focus on customer taxes field."),
    async run(actions) {
        await actions.click();
        const e = queryFirst(
            ".o_field_widget[name=taxes_id] .o-autocomplete--dropdown-item:not(.o_m2o_dropdown_option) > a"
        );
        if (e) {
            await actions.click(e);
        } else {
            await actions.click(); // close dropdown
        }
    },
}, {
    trigger: '.o_field_widget[name=service_policy] select',
    content: _t('Change service policy'),
    position: 'left',
    run: `select "delivered_timesheet"`,
}, {
    trigger: '.o_field_widget[name=service_tracking] select',
    content: _t('Change track service'),
    position: 'left',
    run: `select "task_global_project"`,
}, {
    isActive: ["desktop"],
    trigger: '.o_field_widget[name=project_id] input',
    content: _t('Choose project'),
    position: 'left',
    run: "edit the_flow.project",
}, {
    isActive: ["mobile"],
    trigger: '.o_field_widget[name=project_id] input',
    content: _t('Choose project'),
    position: 'left',
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".modal-dialog .btn:contains('New')",
    content: _t("Click here to add new line."),
    position: "left",
    run: "click",
},
{
     in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Project')",
},
{
    isActive: ["mobile"],
    trigger: '.o_field_widget[name=name] textarea',
    content: _t('Let\'s enter the name.'),
    position: 'left',
    run: "edit the_flow.project",
}, {
    isActive: ["auto", "desktop"],
    trigger: ".o-autocomplete--dropdown-item > a:contains('the_flow.project')",
    run: "click",
},
{
     in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Project')",
},
{
    isActive: ["mobile"],
    trigger: ".modal-footer .btn-primary:contains('Save')",
    content: _t('Save'),
    position: 'right',
    run: "click",
}, {
    trigger: '.o_form_status_indicator .o_form_button_save',
    content: _t("Save this product and the modifications you've made to it."),
    position: 'bottom',
    run: "click",
}, {
// Create an opportunity
    isActive: ["enterprise"],
    trigger: '.o_menu_toggle',
    content: _t('Go back to the home menu'),
    position: 'bottom',
    run: "click",
},
...stepUtils.goToAppSteps('crm.crm_menu_root', markup(_t('Organize your sales activities with the <b>CRM app</b>.'))),
{
    trigger: '.o_opportunity_kanban',
},
{
    trigger: ".o-kanban-button-new",
    content: markup(_t("Click here to <b>create your first opportunity</b> and add it to your pipeline.")),
    position: "bottom",
    run: "click",
}, {
    trigger: ".o_kanban_quick_create .o_field_widget[name=name] input",
    content: markup(_t("<b>Choose a name</b> for your opportunity.")),
    position: "right",
    run: "edit the_flow.opportunity",
}, {
    isActive: ["desktop"],
    trigger: ".o_kanban_quick_create .o_field_widget[name=partner_id] input",
    content: _t("Write the name of your customer to create one on the fly, or select an existing one."),
    position: "left",
    run: "edit the_flow.customer",
}, {
    isActive: ["mobile"],
    trigger: ".o_kanban_quick_create .o_field_widget[name=partner_id] input",
    content: _t("Write the name of your customer to create one on the fly, or select an existing one."),
    position: "left",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".modal-dialog .btn:contains('New')",
    content: _t("Click here to add new line."),
    position: "left",
    run: "click",
},
{
     in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Organization / Contact')",
},
{
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=name] input:not(.o_invisible_modifier)",
    content: _t('Let\'s enter the name.'),
    position: 'left',
    run: "edit the_flow.customer",
}, {
    isActive: ["auto", "desktop"],
    trigger: ".ui-menu-item > a:contains('the_flow.customer')",
    run: "click",
},
{
     in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Organization / Contact')",
},
{
    isActive: ["mobile"],
    trigger: ".modal-footer .btn-primary:contains('Save')",
    content: _t('Save'),
    position: 'right',
    run: "click",
},
{
    trigger: ".o_kanban_quick_create .o_field_widget[name=partner_id] .o_external_button", // Wait name_create
},
{
    trigger: ".o_kanban_quick_create .o_kanban_add",
    content: markup(_t("Click here to <b>add your opportunity</b>.")),
    position: "right",
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: ".o_kanban_group:first .o_kanban_record span:contains('the_flow.opportunity')",
    content: markup(_t("<b>Drag &amp; drop opportunities</b> between columns as you progress in your sales cycle.")),
    position: "right",
    run: "drag_and_drop(.o_opportunity_kanban .o_kanban_group:eq(2))",
}, {
    isActive: ["desktop"],
    trigger: ".o_kanban_group:eq(2) > .o_kanban_record span:contains('the_flow.opportunity')",
    content: _t("Click on an opportunity to zoom to it."),
    position: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_kanban_group:first .o_kanban_record span:contains('the_flow.opportunity')",
    content: _t("Open the_flow.opportunity"),
    position: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_statusbar_status .dropdown-toggle:visible",
    content: _t("Change status from New to proposition."),
    position: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".dropdown-item:contains('Proposition')",
    content: _t("Change status from New to proposition."),
    position: "bottom",
    run: "click",
},
// Create a quotation
...stepUtils.statusbarButtonsSteps('New Quotation', markup(_t('<p><b>Create a quotation</p>'))),
{
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=order_line] .o_field_x2many_list_row_add > a",
    content: _t("Click here to add some lines to your quotations."),
    position: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=order_line] .btn:contains(Add)",
    content: _t("Click here to add some lines to your quotations."),
    position: "bottom",
    run: "click",
}, {
    /**
     * We need both triggers because the "sale_product_configurator" module replaces the
     * "product_id" field with a "product_template_id" field.
     * This selector will still only ever select one element.
     */
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
    content: _t("Select a product, or create a new one on the fly. The product will define the default sales price (that you can change), taxes and description automatically."),
    position: "right",
    run: "edit the_flow.product",
}, {
    isActive: ["desktop"],
    trigger: ".ui-menu-item > a:contains('the_flow.product')",
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: "td[name='product_id'][data-tooltip*='the_flow.product'], td[name='product_template_id'][data-tooltip*='the_flow.product']",
}, {
    isActive: ["desktop"],
    trigger: "td[name='product_uom'][data-tooltip='Units']",
},
{
     in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Order Lines')",
},
{
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=product_id] input",
    content: _t("Select a product, or create a new one on the fly. The product will define the default sales price (that you can change), taxes and description automatically."),
    position: "right",
    run: "click",
},
...stepUtils.mobileKanbanSearchMany2X('Product', 'the_flow.product'),
{
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=order_line] .o_field_x2many_list_row_add > a",
    content: _t("Click here to add some lines to your quotations."),
    position: "bottom",
    run: "click",
},
{
     in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Order Lines')",
},
{
    isActive: ["mobile"],
    trigger: ".modal-footer .btn-primary:contains('Save & New')",
    content: _t('Save & New'),
    position: 'right',
    run: "click",
}, {
    // check if the new record is displayed
    isActive: ["mobile"],
    trigger: ".modal-footer .btn-primary:contains('Save & New'):not([disabled])",
},
{
    isActive: ["desktop"],
    trigger: '.o_field_widget[name=order_line] .o_data_row:nth-child(2).o_selected_row',
},
{
    /**
     * We need both triggers because the "sale_product_configurator" module replaces the
     * "product_id" field with a "product_template_id" field.
     * This selector will still only ever select one element.
     */
    isActive: ["desktop"],
    trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
    content: _t("Select a product"),
    position: "right",
    run: "edit the_flow.service",
}, {
    isActive: ["desktop"],
    trigger: ".ui-menu-item > a:contains('the_flow.service')",
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: "td[name='product_id'][data-tooltip*='the_flow.service'], td[name='product_template_id'][data-tooltip*='the_flow.service']",
}, {
    isActive: ["desktop"],
    trigger: "td[name='product_uom'][data-tooltip='Hours']",
}, {
    isActive: ["desktop"],
    trigger: 'label:contains("Untaxed Amount")',
    run: "click",
    // click somewhere else to exit cell focus
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: '.o_field_widget[name=order_line] .oe_kanban_card:contains(the_flow.product)',
},
{
    isActive: ["mobile"],
    trigger: ".o_field_widget[name=product_id] input",
    content: _t("Select a product, or create a new one on the fly. The product will define the default sales price (that you can change), taxes and description automatically."),
    position: "right",
    run: "click",
},
...stepUtils.mobileKanbanSearchMany2X('Product', 'the_flow.service'),
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: ".modal:not(.o_inactive_modal) .modal-title:contains('Order Lines')",
},
{
    isActive: ["mobile"],
    trigger: ".modal-footer .btn-primary:contains('Save & Close')",
    content: _t('Save & Close'),
    position: 'right',
    run: "click",
},
...stepUtils.statusbarButtonsSteps('Send by Email', _t("Try to send it to email"), ".o_statusbar_status .dropdown-toggle:contains('Quotation')"),
{
    isActive: ["body:not(:has(.modal-footer button[name='action_send_mail']))"],
    trigger: ".modal-footer button[name='document_layout_save']",
    content: _t("let's continue"),
    position: "bottom",
    run: "click",
}, {
    trigger: ".o_field_widget[name=email] input",
    content: _t("Enter an email address"),
    position: "right",
    run: "edit test@the_flow.com",
}, {
    trigger: ".modal-footer .btn-primary",
    content: _t("Save your changes"),
    position: "bottom",
    run: "click",
}, {
    trigger: ".modal-footer .btn-primary:contains('Send')",
    content: _t("Try to send it to email"),
    position: "bottom",
    run: "click",
},
...stepUtils.statusbarButtonsSteps('Confirm', markup(_t("<p>Confirm this quotation</p>"))),
{
    isActive: ["enterprise"],
    trigger: '.o_menu_toggle',
    content: _t('Go back to the home menu'),
    position: 'bottom',
    run: "click",
},
...stepUtils.goToAppSteps('stock.menu_stock_root', _t('Go to Inventory')),
{
    isActive: ["mobile"],
    trigger: ".o_breadcrumb .active:contains('Inventory Overview')",
},
{
    isActive: ["mobile"],
    trigger: ".o_mobile_menu_toggle",
    content: _t("Open bugger menu."),
    position: "bottom",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: '.o_main_navbar',
},
{
    isActive: ["desktop"],
    trigger: ".o_menu_sections button[data-menu-xmlid='stock.menu_stock_warehouse_mgmt']",
    content: _t("Go to Operations"),
    position: "bottom",
    run: "click",
}, {
    trigger: ".dropdown-item[data-menu-xmlid='stock.menu_reordering_rules_replenish'], nav.o_burger_menu_content li[data-menu-xmlid='stock.menu_reordering_rules_replenish']",
    content: _t("Replenishment"),
    position: "bottom",
    run: "click",
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: "span:contains('Replenishment')",
},
{
    isActive: ["mobile"],
    trigger: ".o_control_panel_navigation .btn .fa-search",
    run: "click",
}, {
    trigger: ".o_searchview_facet:contains('To Reorder') .o_facet_remove",
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: "td:contains('the_flow.component2')",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: "span:contains('the_flow.component2')",
    run: "click",
},
{
    // FIXME WOWL: remove first part of selector when legacy view is dropped
    trigger: "input.o_field_widget[name=product_min_qty], .o_field_widget[name=product_min_qty] input",
    content: _t("Set the minimum product quantity"),
    position: "right",
    run: "edit 1",
}, {
    // FIXME WOWL: remove first part of selector when legacy view is dropped
    trigger: "input.o_field_widget[name=product_max_qty], .o_field_widget[name=product_max_qty] input",
    content: _t("Set the maximum product quantity"),
    position: "right",
    run: "edit 10",
}, {
    isActive: ["desktop"],
    trigger: ".o_list_button_save",
    content: markup(_t("<p>Save this reordering rule</p>")),
    position: "bottom",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_form_button_save",
    content: markup(_t("<p>Save this reordering rule</p>")),
    position: "bottom",
    run: "click",
}, {
//Go to purchase:
    isActive: ["enterprise"],
    trigger: '.o_menu_toggle',
    content: _t('Go back to the home menu'),
    position: 'bottom',
    run: "click",
},
...stepUtils.goToAppSteps('purchase.menu_purchase_root', _t('Go to Purchase')),
{
    isActive: ["desktop"],
    trigger: '.o_data_row:has(.o_data_cell:contains("the_flow.vendor")) .o_data_cell:first',
    content: _t('Select the generated request for quotation'),
    position: 'bottom',
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: '.o_kanban_record .o_kanban_record_title:contains("the_flow.vendor")',
    content: _t('Select the generated request for quotation'),
    position: 'bottom',
    run: "click",
},
...stepUtils.statusbarButtonsSteps('Confirm Order', _t("Confirm quotation")),
...stepUtils.statusbarButtonsSteps('Receive Products', _t("Receive Product"), ".o_statusbar_status .dropdown-toggle:contains('Purchase Order')"),
...stepUtils.statusbarButtonsSteps('Validate', _t("Validate"), ".o_statusbar_status:contains('Ready')"),
{
    trigger: ".o_back_button, .breadcrumb-item:not('.active'):last",
    content: _t('go back to the purchase order'),
    position: 'bottom',
    run: "click",
},
...stepUtils.statusbarButtonsSteps('Create Bill', _t('go to Vendor Bills'), ".o_statusbar_status .dropdown-toggle:contains('Purchase Order')"),
{
    trigger: ".o_form_label .o_field_widget:contains('Vendor Bill')",
},
{
    trigger:".o_field_widget[name=invoice_date] input",
    content: _t('Set the invoice date'),
    run: "edit 01/01/2020 && click body",
},
...stepUtils.statusbarButtonsSteps('Confirm', _t("Try to send it to email"), ".o_statusbar_status .o_arrow_button_current:contains('Draft')"),
...stepUtils.statusbarButtonsSteps('Register Payment', _t("Register Payment"), ".o_statusbar_status .o_arrow_button_current:contains('Posted')"),
{
    trigger: ".modal-footer .btn-primary",
    content: _t("Validate"),
    position: "bottom",
    run: "click",
}, {
    isActive: ["enterprise"],
    trigger: '.o_menu_toggle',
    content: _t('Go back to the home menu'),
    position: 'bottom',
    run: "click",
},
...stepUtils.goToAppSteps('mrp.menu_mrp_root', _t('Go to Manufacturing')),
{
    isActive: ["mobile"],
    trigger: ".o_breadcrumb .active:contains('Manufacturing Orders'), .o_breadcrumb .active:contains('Work Centers Overview')",
},
{
    isActive: ["mobile"],
    trigger: ".o_mobile_menu_toggle",
    content: _t("Open bugger menu."),
    position: "bottom",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_menu_sections button[data-menu-xmlid='mrp.menu_mrp_manufacturing']",
    content: _t('Click on Operations menuitem'),
    position: 'bottom',
    run: "click",
}, {
    trigger: ".dropdown-item[data-menu-xmlid='mrp.menu_mrp_production_action'], nav.o_burger_menu_content li[data-menu-xmlid='mrp.menu_mrp_production_action']",
    content: _t('Open manufacturing orders'),
    position: 'bottom',
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: '.o_data_row:has(.o_data_cell:contains("the_flow.product")):first .o_data_cell:first',
    content: _t('Select the generated manufacturing order'),
    position: 'bottom',
    run: "click",
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: ".o_breadcrumb .active:contains('Manufacturing Orders')",
},
{
    isActive: ["mobile"],
    trigger: '.o_kanban_record .o_kanban_record_title:contains("the_flow.product"):first',
    content: _t('Select the generated manufacturing order'),
    position: 'bottom',
    run: "click",
}, {
    trigger: ".o_field_widget[name=qty_producing] input",
    content: _t('Set the quantity producing'),
    position: "right",
    run: "edit 1 && click body",
},
...stepUtils.statusbarButtonsSteps('Produce All', _t("Produce All"), ".o_statusbar_status .dropdown-toggle:contains('To Close')"),
{
    isActive: ["enterprise"],
    trigger: '.o_menu_toggle',
    content: _t('Go back to the home menu'),
    position: 'bottom',
    run: "click",
},
...stepUtils.goToAppSteps('sale.sale_menu_root', markup(_t('Organize your sales activities with the <b>Sales app</b>.'))),
{
    isActive: ["mobile"],
    trigger: ".o_breadcrumb .active:contains('Quotations')",
},
{
    isActive: ["mobile"],
    trigger: ".o_mobile_menu_toggle",
    content: _t("Open bugger menu."),
    position: "bottom",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: ".o_menu_sections button[data-menu-xmlid='sale.sale_order_menu']",
    content: _t("Go to Sales menu"),
    position: "bottom",
    run: "click",
}, {
    trigger: ".dropdown-item[data-menu-xmlid='sale.menu_sale_order'], nav.o_burger_menu_content li[data-menu-xmlid='sale.menu_sale_order']",
    content: _t("Go to the sales orders"),
    position: "bottom",
    run: "click",
},
{
    isActive: ["desktop"],
    trigger: '.o_control_panel .o_breadcrumb:contains("Sales Orders")',
},
{
    isActive: ["desktop"],
    trigger: ".o_data_cell:contains('the_flow.customer')",
    content: _t("Go to the last sale order"),
    position: "right",
    run: "click",
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: '.o_control_panel .o_breadcrumb:contains("Sales Orders")',
},
{
    isActive: ["mobile"],
    trigger: ".o_kanban_record .o_kanban_record_title:contains('the_flow.customer')",
    content: _t("Go to the last sale order"),
    position: "bottom",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: '.o_control_panel .o_breadcrumb:contains("S0")',
},
stepUtils.mobileModifier(stepUtils.autoExpandMoreButtons()),
{
    isActive: ["desktop"],
    trigger: '.oe_stat_button:has(div[name=tasks_count])',
    content: _t('See Tasks'),
    position: 'right',
    run: "click",
},
{
    in_modal: false,
    isActive: ["mobile"],
    trigger: '.o_control_panel .o_breadcrumb:contains("S0")',
},
{
    isActive: ["mobile"],
    trigger: '.oe_stat_button:has(div[name=tasks_count])',
    content: _t('See Tasks'),
    position: 'bottom',
    run: "click",
},
{
    trigger: 'div.o_notebook_headers',
},
{
    trigger: 'a.nav-link:contains(Timesheets)',
    content: 'Click on Timesheets page to log a timesheet',
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: 'div[name="timesheet_ids"] td.o_field_x2many_list_row_add a[role="button"]',
    content: 'Click on Add a line to create a new timesheet into the task.',
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: '.o-kanban-button-new',
    content: _t('Open the full search field'),
    position: 'bottom',
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: 'div[name="timesheet_ids"] div[name="name"] input',
    content: 'Enter a description this timesheet',
    run: "edit 10 hours",
}, {
    isActive: ["mobile"],
    trigger: '.modal-content.o_form_view div[name="name"] input',
    content: 'Enter a description this timesheet',
    run: "edit 10 hours",
}, {
    isActive: ["desktop"],
    trigger: 'div[name="timesheet_ids"] div[name="unit_amount"] input',
    content: 'Enter one hour for this timesheet',
    run: "edit 10",
}, {
    isActive: ["mobile"],
    trigger: '.modal-content.o_form_view div[name="unit_amount"] input',
    content: 'Enter one hour for this timesheet',
    run: "edit 10",
}, {
    content: "save",
    trigger: ".o_form_button_save",
    run: "click",
},
{
    isActive: ["mobile"],
    trigger: ".o_breadcrumb .active:contains('the_flow.service')",
},
...stepUtils.goBackBreadcrumbsMobile(
        _t('Back to the sale order')
    ),
{
    isActive: ["desktop"],
    trigger: 'div:not(.o_form_editable)', // Waiting save
},
{
    isActive: ["desktop"],
    trigger: '.breadcrumb-item:nth-child(2) a',
    content: _t('Back to the sale order'),
    position: 'bottom',
    run: "click",
},
...stepUtils.statusbarButtonsSteps('Create Invoice', _t("Validate"), ".o_field_widget[name=order_line]"),
{
    trigger: ".modal-footer .btn-primary",
    content: _t("Create and View Invoices"),
    position: "bottom",
    run: "click",
},
...stepUtils.statusbarButtonsSteps('Confirm', _t("Validate"), ".o_breadcrumb .active:contains('Draft Invoice')"),
...stepUtils.statusbarButtonsSteps('Register Payment', _t("Register Payment"), ".o_statusbar_status .o_arrow_button_current:contains('Posted')"),
{
    trigger: ".modal-footer .btn-primary",
    content: _t("Validate"),
    position: "bottom",
    run: "click",
}, {
    isActive: ["auto", "community"],
    content: "wait for payment registration to succeed",
    trigger: "span.text-bg-success:contains('Paid')",
},{
    isActive: ["enterprise"],
    trigger: '.o_menu_toggle',
    content: _t('Go back to the home menu'),
    position: 'bottom',
    run: "click",
}, {
    isActive: ["enterprise"],
    trigger: '.o_app[data-menu-xmlid="accountant.menu_accounting"]',
    content: _t('Go to Accounting'),
    position: 'bottom',
    run: "click",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: "div.o_account_kanban div.o_kanban_card_header a.oe_kanban_action span:contains('Bank')",
    content: _t("Open the bank reconciliation widget"),
    run: "click",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: "button.o_switch_view.o_list",
    content: _t("Move back to the list view"),
    run: "click",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: "button.o_list_button_add",
    content: _t("Create a new bank transaction"),
    run: "click",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: '.o_field_widget[name=amount] input',
    content: _t("Write the amount received."),
    position: "bottom",
    run: "edit 11.00",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: ".o_selected_row .o_field_widget[name=payment_ref] input",
    content: _t("Let's enter a name."),
    run: "edit the_flow.statement.line",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: ".o_selected_row .o_field_widget[name=partner_id] input",
    content: _t("Write the name of your customer."),
    position: "bottom",
    run: "edit the_flow.customer",
}, {
    isActive: ["auto", "desktop", "enterprise"],
    trigger: ".ui-menu-item > a:contains('the_flow.customer')",
    in_modal: false,
    run: "click",
},
{
    isActive: ["enterprise", "desktop"],
    trigger: ".o_selected_row .o_field_widget[name=partner_id] .o_external_button",
},
{
    isActive: ["enterprise", "desktop"],
    trigger: '.o_list_button_save',
    content: _t('Save.'),
    position: 'bottom',
    run: "click",
},
{
    isActive: ["enterprise", "desktop"],
    trigger: ".o_list_button_add",
},
{
    isActive: ["enterprise", "desktop"],
    trigger: "button.o_switch_view.o_kanban",
    content: _t("Move back to the kanban view"),
    run: "click",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: "div.o_bank_rec_st_line_kanban_card span:contains('the_flow.customer')",
},
{
    isActive: ["enterprise", "desktop"],
    trigger: "div.o_bank_rec_st_line_kanban_card span:contains('the_flow.customer')",
    content: _t("Select the newly created bank transaction"),
    run: "click",
}, {
    isActive: ["enterprise", "desktop"],
    trigger: "button.btn-primary:contains('Validate')",
    content: _t("Reconcile the bank transaction"),
    run: "click",
},
// exit reconciliation widget
{
    isActive: ["auto", "desktop"],
    ...stepUtils.toggleHomeMenu(),
    run: "click",
},
{
    isActive: ["auto", "desktop", "enterprise"],
    trigger: `.o_app[data-menu-xmlid="accountant.menu_accounting"]`,
    run: "click",
},
{
    isActive: ["auto", "desktop", "enterprise"],
    content: "check that we're back on the dashboard",
    trigger: 'a:contains("Customer Invoices")',
}]});
