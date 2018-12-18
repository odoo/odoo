odoo.define('sale.product_configurator_pricelist_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

tour.register('sale_product_configurator_pricelist_tour', {
    url: "/web",
    test: true,
},
[
tour.STEPS.SHOW_APPS_MENU_ITEM,
{
    content: "navigate to the sale app",
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'community'
}, {
    content: "navigate to the sale app",
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'enterprise'
}, {
    content: "create a new order",
    trigger: '.o_list_button_add',
    extra_trigger: ".o_sale_order"
}, {
    content: "search the partner",
    trigger: 'div[name="partner_id"] input',
    run: 'text Azure'
}, {
    content: "select the partner",
    trigger: 'ul.ui-autocomplete > li > a:contains(Azure)',
}, {
    content: "search the pricelist",
    trigger: 'div[name="pricelist_id"] input',
    run: 'text Public Pricelist'
}, {
    content: "select the pricelist",
    trigger: 'ul.ui-autocomplete > li > a:contains(Public Pricelist)',
}, {
    content: "wait for pricelist to be set",
    trigger: 'div.o_with_button[name="pricelist_id"]',
    run: function () {},
}, {
    content: "open product configurator",
    trigger: 'a:contains("Configure a product")',
}, {
    content: "open product selector",
    trigger: '.o_product_configurator .o_input_dropdown input',
    run: 'click'
}, {
    content: "select desk",
    trigger: 'li a:contains("Customizable Desk")',
    in_modal: false,
    extra_trigger: 'ul.ui-autocomplete',
}, {
    content: "check price is correct (USD)",
    trigger: 'span.oe_currency_value:contains("750.00")',
    run: function () {} // check price
}, {
    content: "add one more",
    trigger: 'button.js_add_cart_json:has(i.fa-plus)',
}, {
    content: "check price for 2",
    trigger: 'span.oe_currency_value:contains("600.00")',
    run: function () {} // check price (pricelist has discount for 2)
}, {
    content: "click add",
    trigger: '.o_sale_product_configurator_add:not(.disabled)'
}, {
    content: "check we are on the add modal",
    trigger: '.td-product_name:contains("Customizable Desk (Steel, White)")',
    extra_trigger: '.oe_optional_products_modal',
    run: 'click'
}, {
    content: "add conference chair",
    trigger: '.js_product:has(strong:contains(Conference Chair)) .js_add',
    extra_trigger: '.oe_optional_products_modal .js_product:has(strong:contains(Conference Chair))',
    run: 'click'
}, {
    content: "add chair floor protection",
    trigger: '.js_product:has(strong:contains(Chair floor protection)) .js_add',
    extra_trigger: '.oe_optional_products_modal .js_product:has(strong:contains(Chair floor protection))',
    run: 'click'
}, {
    content: "verify configurator final price", // tax excluded
    trigger: '.o_total_row .oe_currency_value:contains("1,257.00")',
}, {
    content: "add to SO",
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_optional_products_modal',
    run: 'click'
}, {
    content: "verify SO final price excluded",
    trigger: 'span[name="amount_untaxed"]:contains("1,257.00")',
}, {
    content: "verify SO final price included",
    trigger: 'span[name="amount_total"]:contains("1,437.00")',
}
]);

});
