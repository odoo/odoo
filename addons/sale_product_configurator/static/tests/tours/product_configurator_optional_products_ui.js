odoo.define('sale.product_configurator_optional_products_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

tour.register('sale_product_configurator_optional_products_tour', {
    url: "/web",
    test: true,
}, [tour.stepUtils.showAppsMenuItem(), {
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
    run: function () {
        var $input = $('div[name="product_template_id"] input');
        $input.click();
        $input.val('Customizable Desk');
        var keyDownEvent = jQuery.Event("keydown");
        keyDownEvent.which = 42;
        $input.trigger(keyDownEvent);
    }
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
    run: 'click'
}, {
    trigger: '.o_sale_product_configurator_add'
}, {
    trigger: 'tr:has(.td-product_name:contains("Office Chair Black")) .js_add',
}, {
    trigger: 'tr:has(.td-product_name:contains("Customizable Desk")) .fa-plus'
}, {
    trigger: 'tr:has(.td-product_name:contains("Chair floor protection")) .js_add',
}, {
    content: 'Is below its parent 1',
    trigger: 'tr:has(.td-product_name:contains("Office Chair Black")) + tr:has(.td-product_name:contains("Chair floor protection"))'
}, {
    trigger: 'tr:has(.td-product_name:contains("Conference Chair")) .js_add',
}, {
    trigger: 'tr:has(.td-product_name:contains("Conference Chair")) .fa-minus'
}, {
    trigger: 'tr:has(.td-product_name:contains("Chair floor protection")) .js_add',
}, {
    content: 'Is below its parent 2',
    trigger: 'tr:has(.td-product_name:contains("Conference Chair")) + tr:has(.td-product_name:contains("Chair floor protection"))'
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_optional_products_modal',
    run: 'click'
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Customizable Desk")) td.o_data_cell:contains("2.0")',
    extra_trigger: 'div[name="order_line"]',
    run: function () {}, // check added product
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Office Chair Black")) td.o_data_cell:contains("1.0")',
    extra_trigger: 'div[name="order_line"]',
    run: function () {}, // check added product
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Conference Chair")) td.o_data_cell:contains("1.0")',
    extra_trigger: 'div[name="order_line"]',
    run: function () {}, // check added product
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Chair floor protection")):nth(0) td.o_data_cell:contains("1.0")',
    extra_trigger: 'div[name="order_line"]',
    run: function () {}, // check added product
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Chair floor protection")):nth(1) td.o_data_cell:contains("1.0")',
    extra_trigger: 'div[name="order_line"]',
    run: function () {}, // check added product
}]);

});
