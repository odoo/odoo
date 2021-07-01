odoo.define('sale.sale_product_configurator_advanced_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

var optionVariantImage;

tour.register('sale_product_configurator_advanced_tour', {
    url: "/web",
    test: true,
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',  // Note: The module sale_management is mandatory
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
    trigger: "a:contains('Add a product')",
    extra_trigger: ".o_field_widget[name=partner_shipping_id] .o_external_button", // Wait for onchange_partner_id
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
    trigger: 'span:contains("Custom")',
    extra_trigger: '.oe_advanced_configurator_modal',
    run: 'click'
}, {
    trigger: '.oe_advanced_configurator_modal ul.js_add_cart_variants li[data-attribute_id]:nth-child(1) .variant_custom_value',
    extra_trigger: '.oe_advanced_configurator_modal',
    run: 'text Custom 1'
}, {
    trigger: '.oe_advanced_configurator_modal ul.js_add_cart_variants li[data-attribute_id]:nth-child(3) span:contains("PAV9")',
    extra_trigger: '.oe_advanced_configurator_modal',
    run: 'click'
}, {
    trigger: '.oe_advanced_configurator_modal ul.js_add_cart_variants li[data-attribute_id]:nth-child(3) .variant_custom_value',
    extra_trigger: '.oe_advanced_configurator_modal',
    run: 'text Custom 2'
}, {
    trigger: '.oe_advanced_configurator_modal ul.js_add_cart_variants li[data-attribute_id]:nth-child(4) span:contains("PAV5")',
    extra_trigger: '.oe_advanced_configurator_modal',
    run: 'click'
}, {
    trigger: '.oe_advanced_configurator_modal ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) select ',
    extra_trigger: '.oe_advanced_configurator_modal',
    run: function (){
        var inputValue = $('.oe_advanced_configurator_modal ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) option[data-value_name="PAV9"]').val();
        $('.oe_advanced_configurator_modal ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) select').val(inputValue);
        $('.oe_advanced_configurator_modal ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) select').trigger('change');
    }
}, {
    trigger: '.oe_advanced_configurator_modal ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) .variant_custom_value',
    extra_trigger: '.oe_advanced_configurator_modal',
    run: 'text Custom 3'
}, {
    trigger: '.main_product strong:contains("Custom, White, PAV9, PAV5, PAV1")',
    extra_trigger: '.oe_advanced_configurator_modal',
    run: function () {} //check
}, {
    trigger: '.oe_advanced_configurator_modal .js_product:eq(1) div:contains("Conference Chair (TEST) (Steel)")',
    run: function () {
        optionVariantImage = $('.oe_advanced_configurator_modal .js_product:eq(1) img.variant_image').attr('src');
    }
}, {
    trigger: '.oe_advanced_configurator_modal .js_product:eq(1) input[data-value_name="Aluminium"]',
}, {
    trigger: '.oe_advanced_configurator_modal .js_product:eq(1) div:contains("Conference Chair (TEST) (Aluminium)")',
    run: function () {
        var newVariantImage = $('.oe_advanced_configurator_modal .js_product:eq(1) img.variant_image').attr('src');
        if (newVariantImage !== optionVariantImage) {
            $('<p>').text('image variant option src changed').insertAfter('.oe_advanced_configurator_modal .js_product:eq(1) .product-name');
        }

    }
}, {
    extra_trigger: '.oe_advanced_configurator_modal .js_product:eq(1) div:contains("image variant option src changed")',
    trigger: '.oe_advanced_configurator_modal .js_product:eq(1) input[data-value_name="Steel"]',
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_advanced_configurator_modal',
    run: 'click'
}, {
    trigger: 'td.o_data_cell:contains("Customizable Desk (TEST) (Custom, White, PAV9, PAV5, PAV1)")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("Legs: Custom: Custom 1")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PA1: PAV9: Custom 2")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PA4: PAV9: Custom 3")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PA5: PAV1")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PA7: PAV1")',
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
