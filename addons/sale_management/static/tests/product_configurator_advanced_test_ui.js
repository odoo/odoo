odoo.define('sale.sale_product_configurator_advanced_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

tour.register('sale_product_configurator_advanced_tour', {
    url: "/web",
    test: true,
}, [tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'enterprise'
},  {
    trigger: ".o_list_button_add",
    extra_trigger: ".o_sale_order"
}, {
    trigger: ".o_required_modifier[name=partner_id] input",
    run: "text Tajine Saucisse",
}, {
    trigger: ".ui-menu-item > a:contains('Tajine Saucisse')",
    auto: true,
}, {
    trigger: "a:contains('Configure a product')",
    extra_trigger: ".o_field_widget[name=pricelist_id] > .o_external_button", // Wait for pricelist (onchange_partner_id)
}, {
    trigger: '.o_product_configurator .o_input_dropdown input',
    run: 'click'
}, {
    trigger: 'li a:contains("Customizable Desk")',
    in_modal: false,
    extra_trigger: 'ul.ui-autocomplete',
    run: 'click'
}, {
    trigger: 'span:contains("Custom")',
    extra_trigger: '.o_product_configurator',
    run: 'click'
}, {
    trigger: '.o_product_configurator ul.js_add_cart_variants li[data-attribute_id]:nth-child(1) .variant_custom_value',
    extra_trigger: '.o_product_configurator',
    run: 'text Custom 1'
}, {
    trigger: '.o_product_configurator ul.js_add_cart_variants li[data-attribute_id]:nth-child(3) span:contains("PAV9")',
    extra_trigger: '.o_product_configurator',
    run: 'click'
}, {
    trigger: '.o_product_configurator ul.js_add_cart_variants li[data-attribute_id]:nth-child(3) .variant_custom_value',
    extra_trigger: '.o_product_configurator',
    run: 'text Custom 2'
}, {
    trigger: '.o_product_configurator ul.js_add_cart_variants li[data-attribute_id]:nth-child(4) span:contains("PAV5")',
    extra_trigger: '.o_product_configurator',
    run: 'click'
}, {
    trigger: '.o_product_configurator ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) select ',
    extra_trigger: '.o_product_configurator',
    run: function (){
        var inputValue = $('.o_product_configurator ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) option[data-value_name="PAV9"]').val();
        $('.o_product_configurator ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) select').val(inputValue);
        $('.o_product_configurator ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) select').trigger('change');
    }
}, {
    trigger: '.o_product_configurator ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) .variant_custom_value',
    extra_trigger: '.o_product_configurator',
    run: 'text Custom 3'
}, {
    trigger: ".o_sale_product_configurator_add",
    run: 'click'
}, {
    trigger: '.main_product strong:contains("White, Custom, PAV9, PAV5, PAV1")',
    extra_trigger: '.oe_optional_products_modal',
    run: function () {} //check
}, {
    trigger: '.main_product div:contains("Custom: Custom 1")',
    extra_trigger: '.oe_optional_products_modal',
    run: function () {} //check
}, {
    trigger: '.main_product div:contains("PAV9: Custom 2")',
    extra_trigger: '.oe_optional_products_modal',
    run: function () {} //check
}, {
    trigger: '.main_product div:contains("PAV9: Custom 3")',
    extra_trigger: '.oe_optional_products_modal',
    run: function () {} //check
}, {
    trigger: '.main_product div:contains("PA5: PAV1")',
    extra_trigger: '.oe_optional_products_modal',
    run: function () {} //check
}, {
    trigger: '.main_product div:contains("PA5: PAV1")',
    extra_trigger: '.oe_optional_products_modal',
    run: function () {} //check
}, {
    trigger: '.main_product div:contains("PA8: PAV1")',
    extra_trigger: '.oe_optional_products_modal',
    run: function () {} //check
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_optional_products_modal',
    run: 'click'
}, {
    trigger: 'td.o_data_cell:contains("Customizable Desk (White, Custom, PAV9, PAV5, PAV1)")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("Custom: Custom 1")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PAV9: Custom 2")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PAV9: Custom 3")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PA5: PAV1")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PA5: PAV1")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PA8: PAV1")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){} //check
}]);

});
