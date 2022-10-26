/** @odoo-module **/

import tour from 'web_tour.tour';

let optionVariantImage;

tour.register('sale_product_configurator_advanced_tour', {
    url: '/web',
    test: true,
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
},  {
    trigger: '.o_list_button_add',
    extra_trigger: '.o_sale_order'
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: 'text Tajine Saucisse',
}, {
    trigger: '.ui-menu-item > a:contains("Tajine Saucisse")',
    auto: true,
}, {
    trigger: 'a:contains("Add a product")',
    extra_trigger: '.o_field_widget[name=partner_shipping_id] .o_external_button', // Wait for onchange_partner_id
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Custo',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
}, {
    trigger: 'span:contains("Custom")',
    extra_trigger: '.oe_advanced_configurator_modal',
}, {
    trigger: 'ul.js_add_cart_variants li[data-attribute_id]:nth-child(1) .variant_custom_value',
    run: 'text Custom 1'
}, {
    trigger: 'ul.js_add_cart_variants li[data-attribute_id]:nth-child(3) div:contains("PAV9") input',
}, {
    trigger: 'ul.js_add_cart_variants li[data-attribute_id]:nth-child(3) .variant_custom_value',
    run: 'text Custom 2'
}, {
    trigger: 'ul.js_add_cart_variants li[data-attribute_id]:nth-child(4) div:contains("PAV5") input',
}, {
    trigger: 'ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) select ',
    run: function (){
        let inputValue = $('.oe_advanced_configurator_modal ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) option[data-value_name="PAV9"]').val();
        $('.oe_advanced_configurator_modal ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) select').val(inputValue);
        $('.oe_advanced_configurator_modal ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) select').trigger('change');
    }
}, {
    trigger: 'ul.js_add_cart_variants li[data-attribute_id]:nth-child(6) .variant_custom_value',
    run: 'text Custom 3'
}, {
    trigger: '.main_product strong:contains("Custom, White, PAV9, PAV5, PAV1")',
    run: function () {} //check
}, {
    trigger: '.js_product:eq(1) div:contains("Conference Chair (TEST) (Steel)")',
    run: function () {
        optionVariantImage = $('.oe_advanced_configurator_modal .js_product:eq(1) img.variant_image').attr('src');
    }
}, {
    trigger: '.js_product:eq(1) input[data-value_name="Aluminium"]',
}, {
    trigger: '.js_product:eq(1) div:contains("Conference Chair (TEST) (Aluminium)")',
    run: function () {
        let newVariantImage = $('.oe_advanced_configurator_modal .js_product:eq(1) img.variant_image').attr('src');
        if (newVariantImage !== optionVariantImage) {
            $('<p>').text('image variant option src changed').insertAfter('.oe_advanced_configurator_modal .js_product:eq(1) .product-name');
        }

    }
}, {
    trigger: '.js_product:eq(1) input[data-value_name="Steel"]',
    extra_trigger: '.js_product:eq(1) div:contains("image variant option src changed")',
}, {
    trigger: 'button span:contains(Confirm)',
}, {
    trigger: 'td.o_data_cell:contains("Customizable Desk (TEST) (Custom, White, PAV9, PAV5, PAV1)")',
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("Legs: Custom: Custom 1")',
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PA1: PAV9: Custom 2")',
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PA4: PAV9: Custom 3")',
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PA5: PAV1")',
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PA7: PAV1")',
    run: function (){} //check
}, {
    trigger: 'td.o_data_cell:contains("PA8: PAV1")',
    run: function (){} //check
}, ...tour.stepUtils.discardForm()
]);
