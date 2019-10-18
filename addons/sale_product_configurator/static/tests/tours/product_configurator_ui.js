odoo.define('sale.product_configurator_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

// Note: please keep this test without pricelist for maximum coverage.
// The pricelist is tested on the other tours.

tour.register('sale_product_configurator_tour', {
    url: "/web",
    test: true,
}, [tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'enterprise'
}, {
    trigger: ".o_list_button_add",
    extra_trigger: ".o_sale_order"
}, {
    trigger: "a:contains('Add a product')",
}, {
    trigger: 'div[name="product_template_id"] input',
    run: function (){
        var $input = $('div[name="product_template_id"] input');
        $input.click();
        $input.val('Custo');
        // fake keydown to trigger search
        var keyDownEvent = jQuery.Event("keydown");
        keyDownEvent.which = 42;
        $input.trigger(keyDownEvent);
    }
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk")',
    run: 'click'
}, {
    trigger: '.configurator_container span:contains("Steel")',
    run: function () {},
}, {
    trigger: '.configurator_container span:contains("Aluminium")',
    run: 'click'
}, {
    trigger: 'span.oe_currency_value:contains("800.40")',
    run: function (){} // check updated price
}, {
    trigger: 'input[data-value_name="Black"]'
}, {
    trigger: '.o_sale_product_configurator_add.disabled'
}, {
    trigger: 'input[data-value_name="White"]'
}, {
    trigger: '.o_sale_product_configurator_add:not(.disabled)'
}, {
    trigger: 'span:contains("Aluminium")',
    extra_trigger: '.oe_optional_products_modal',
    run: 'click'
}, {
    trigger: '.js_product:has(strong:contains(Conference Chair)) .js_add',
    extra_trigger: '.oe_optional_products_modal .js_product:has(strong:contains(Conference Chair))',
    run: 'click'
}, {
    trigger: '.js_product:has(strong:contains(Chair floor protection)) .js_add',
    extra_trigger: '.oe_optional_products_modal .js_product:has(strong:contains(Chair floor protection))',
    run: 'click'
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_optional_products_modal',
    id: "quotation_product_selected",
    run: 'click'
},
// check that 3 products were added to the SO
{
    trigger: 'td.o_data_cell:contains("Customizable Desk (CONFIG) (Aluminium, White)")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){}
}, {
    trigger: 'td.o_data_cell:contains("Conference Chair (CONFIG) (Aluminium)")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){}
}, {
    trigger: 'td.o_data_cell:contains("Chair floor protection")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){}
}, {
    trigger: '.o_readonly_modifier[name=amount_total]:contains("0.00")',
    in_modal: false,
    run: function (){}
}
]);

});
