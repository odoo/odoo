/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('rental_tour', {
    url: "/web",
    sequence: 240,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale_renting.rental_menu_root"]',
    content: markup(_t("Want to <b>rent products</b>? \n Let's discover Odoo Rental App.")),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: '.dropdown-item[data-menu-xmlid="sale_renting.menu_rental_products"]',
    content: _t("At first, let's create some products to rent."),
    position: 'bottom',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_breadcrumb .active:contains(Products)',
    content: _t("Click here to set up your first rental product."),
    position: 'bottom',
}, {
    trigger: ".o_field_widget[name='name'] textarea",
    content: _t("Enter the product name."),
    position: 'bottom',
}, {
    trigger: '.o_form_button_save',
    content: _t("Save the product."),
    position: 'bottom',
}, {
    trigger: ".nav-item a.nav-link:contains(Rental prices)",
    content: _t("The rental configuration is available here."),
    position: 'top',
}, {
    trigger: 'button[data-menu-xmlid="sale_renting.rental_order_menu"]',
    extra_trigger: '.o_form_button_create', // wait for the new product to be saved
    content: _t("Let's now create an order."),
    position: 'bottom',
}, {
    trigger: '.dropdown-item[data-menu-xmlid="sale_renting.rental_orders_all"]',
    content: _t("Go to the orders menu."),
    position: 'bottom',
}, {
    trigger: '.o-kanban-button-new',
    content: _t("Click here to create a new quotation."),
    position: 'bottom',
}, {
    trigger: ".o_field_widget[name=partner_id] input",
    content: _t("Create or select a customer here."),
    position: 'bottom',
    run: 'text Agrolait',
}, {
    trigger: '.o_field_widget[name=partner_id] .ui-menu-item > a:contains(Agrolait)',
    auto: true,
    in_modal: false,
}, {
    trigger: "a:contains('Add a product')",
    extra_trigger: ".o_field_widget[name='partner_id'] .o_external_button",
    content: _t("Click here to start filling the quotation."),
    position: 'bottom',
}, {
    trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
    content: _t("Select your rental product."),
    position: 'bottom',
}, {
    trigger: ".ui-menu-item a:contains('Test')",
    auto: true,
}, {
    trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
    content: _t("Select the rental dates and check the price."),
    position: 'bottom',
}, {
    trigger: 'td.o_data_cell:contains("Test (Rental)")',
    isCheck: true,
}, {
    trigger: 'button[name=action_confirm]',
    content: _t("Confirm the order when the customer agrees with the terms."),
    position: 'bottom',
}, {
    trigger: 'button[name=action_open_pickup]',
    extra_trigger: '.o_sale_order',
    content: _t("Click here to register the pickup."),
    position: 'bottom',
}, {
    trigger: "button[name='apply']",
    content: _t("Validate the operation after checking the picked-up quantities."),
    position: 'bottom',
}, {
    trigger: "button[name='action_open_return']",
    extra_trigger: '.o_sale_order',
    content: _t("Once the rental is done, you can register the return."),
    position: 'bottom',
}, {
    trigger: "button[name='apply']",
    content: _t("Confirm the returned quantities and hit Validate."),
    position: 'bottom',
}, {
    trigger: '.text-bg-default:contains("Returned")',
    content: _t("You're done with your fist rental. Congratulations!"),
    run() {},
}]});
