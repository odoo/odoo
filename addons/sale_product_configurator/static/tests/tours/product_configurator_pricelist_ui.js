odoo.define('sale.product_configurator_pricelist_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

tour.register('sale_product_configurator_pricelist_tour', {
    url: "/web",
    test: true,
},
[
tour.stepUtils.showAppsMenuItem(),
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
    run: 'text Custom pricelist (TEST)'
}, {
    content: "select the pricelist",
    trigger: 'ul.ui-autocomplete > li > a:contains(Custom pricelist (TEST))',
}, {
    trigger: "a:contains('Add a product')"
}, {
    trigger: 'div[name="product_template_id"] input',
    run: function (){
        var $input = $('div[name="product_template_id"] input');
        $input.click();
        $input.val('Custo');
        var keyDownEvent = jQuery.Event("keydown");
        keyDownEvent.which = 42;
        $input.trigger(keyDownEvent);
    }
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
    run: 'click'
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
    content: "check we are on the add modal",
    trigger: '.td-product_name:contains("Customizable Desk (TEST) (Steel, White)")',
    extra_trigger: '.oe_advanced_configurator_modal',
    run: 'click'
}, {
    content: "add conference chair",
    trigger: '.js_product:has(strong:contains(Conference Chair)) .js_add',
    extra_trigger: '.oe_advanced_configurator_modal .js_product:has(strong:contains(Conference Chair))',
    run: 'click'
}, {
    content: "add chair floor protection",
    trigger: '.js_product:has(strong:contains(Chair floor protection)) .js_add',
    extra_trigger: '.oe_advanced_configurator_modal .js_product:has(strong:contains(Chair floor protection))',
    run: 'click'
}, {
    content: "verify configurator final price", // tax excluded
    trigger: '.o_total_row .oe_currency_value:contains("1,257.00")',
}, {
    content: "add to SO",
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_advanced_configurator_modal',
    run: 'click'
}, {
    content: "verify SO final price excluded",
    trigger: 'span[name="Untaxed Amount"]:contains("1,257.00")',
}, {
    content: "verify SO final price included",
    trigger: 'span[name="amount_total"]:contains("1,437.00")',
}
]);

});
