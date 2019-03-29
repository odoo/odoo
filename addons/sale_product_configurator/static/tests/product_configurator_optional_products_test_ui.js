odoo.define('sale.product_configurator_optional_products_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

tour.register('sale_product_configurator_optional_products_tour', {
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
    trigger: "a:contains('Add a product')"
}, {
    trigger: 'div[name="product_template_id"] input',
    run: function (){
        var $input = $('div[name="product_template_id"] input');
        $input.click();
        $input.val('Office Chair Black');
        var keyDownEvent = jQuery.Event("keydown");
        keyDownEvent.which = 42;
        $input.trigger(keyDownEvent);
    }
}, {
    trigger: 'ul.ui-autocomplete a:contains("Office Chair Black")',
    run: 'click'
}, {
    trigger: '.js_add'
}, {
    trigger: '.js_add_cart_json .fa-plus'
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_optional_products_modal',
    run: 'click'
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Office Chair Black")) td.o_data_cell:contains("2.0")',
    extra_trigger: 'div[name="order_line"]',
    run: function (){} // check added product
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Chair floor protection")) td.o_data_cell:contains("2.0")',
    extra_trigger: 'div[name="order_line"]',
    run: function (){} // check added product
}]);

});
