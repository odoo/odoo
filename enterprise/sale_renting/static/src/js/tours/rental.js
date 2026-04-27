/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('rental_tour', {
    url: "/odoo",
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale_renting.rental_menu_root"]',
    content: markup(_t("Want to <b>rent products</b>? \n Let's discover Odoo Rental App.")),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: '.dropdown-item[data-menu-xmlid="sale_renting.menu_rental_products"]',
    content: _t("At first, let's create some products to rent."),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: ".o_breadcrumb .active:contains(Products)",
},
{
    trigger: '.o-kanban-button-new',
    content: _t("Click here to set up your first rental product."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: ".o_field_widget[name='name'] textarea",
    content: _t("Enter the product name."),
    tooltipPosition: 'bottom',
    run: "edit Test",
}, {
    trigger: '.o_form_button_save',
    content: _t("Save the product."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: ".nav-item a.nav-link:contains(Rental prices)",
    content: _t("The rental configuration is available here."),
    tooltipPosition: 'top',
    run: "click",
},
{
    trigger: ".o_form_button_create", // wait for the new product to be saved
},
{
    trigger: 'button[data-menu-xmlid="sale_renting.rental_order_menu"]:enabled',
    content: _t("Let's now create an order."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: '.dropdown-item[data-menu-xmlid="sale_renting.rental_orders_all"]',
    content: _t("Go to the orders menu."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: '.o-kanban-button-new',
    content: _t("Click here to create a new quotation."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: ".o_field_widget[name=partner_id] input",
    content: _t("Create or select a customer here."),
    tooltipPosition: 'bottom',
    run: "edit Agrolait",
}, {
    isActive: ["auto"],
    trigger: '.o_field_widget[name=partner_id] .ui-menu-item > a:contains(Agrolait)',
    run: "click",
},
{
    trigger: "a:contains('Add a product')",
    content: _t("Click here to start filling the quotation."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
    content: _t("Select your rental product."),
    tooltipPosition: 'bottom',
    run: "edit Test",
}, {
    isActive: ["auto"],
    trigger: ".ui-menu-item a:contains('Test')",
    run: "click",
}, {
    trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
    content: _t("Select the rental dates and check the price."),
    tooltipPosition: 'bottom',
    run: "edit Test",
}, {
    trigger: 'td.o_data_cell:contains("Test (Rental)")',
    run: "click",
}, {
    trigger: "button[name=action_confirm]:enabled",
    content: _t("Confirm the order when the customer agrees with the terms."),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: ".o_sale_order",
},
{
    trigger: "button[name=action_open_pickup]:enabled",
    content: _t("Click here to register the pickup."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: "button[name='apply']",
    content: _t("Validate the operation after checking the picked-up quantities."),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: ".o_sale_order",
},
{
    trigger: "button[name='action_open_return']:enabled",
    content: _t("Once the rental is done, you can register the return."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: "button[name='apply']:enabled",
    content: _t("Confirm the returned quantities and hit Validate."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: '.text-bg-default:contains("Returned")',
    content: _t("You're done with your fist rental. Congratulations!"),
}]});
