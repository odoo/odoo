odoo.define("website_sale_product_configurator.tour_shop_custom_attribute_value", function (require) {
"use strict";
/**
 * Add custom steps to handle the optional products modal introduced
 * by the product configurator module.
 */
var tour = require('web_tour.tour');
require('website_sale.tour_shop_custom_attribute_value');

var optionVariantImage;
var addCartStepIndex = _.findIndex(tour.tours.shop_custom_attribute_value.steps, function (step) {
    return (step.id === 'add_cart_step');
});

tour.tours.shop_custom_attribute_value.steps.splice(addCartStepIndex + 1, 0, {
    trigger: 'div:contains(Custom: Wood)',
    extra_trigger: '.js_product.in_cart.main_product',
    run: function (){} // checks that Yep, it's wood!
}, {
    trigger: 'button.js_add_cart_json:has(i.fa-plus)',
    run: 'click',
}, {
    trigger: 'div.oe_striked_price span:contains(750)',
    run: function (){}, // check
}, {
    trigger: 'span.oe_price span:contains(600)',
    run: function (){}, // check
}, {
    trigger: '.oe_optional_products_modal .js_product:eq(1) div:contains("Conference Chair (CONFIG) (Steel)")',
    run: function () {
        optionVariantImage = $('.oe_optional_products_modal .js_product:eq(1) img.variant_image').attr('src');
    }
}, {
    trigger: '.oe_optional_products_modal .js_product:eq(1) input[data-value_name="Aluminium"]',
}, {
    trigger: '.oe_optional_products_modal .js_product:eq(1) div:contains("Conference Chair (CONFIG) (Aluminium)")',
    run: function () {
        var newVariantImage = $('.oe_optional_products_modal .js_product:eq(1) img.variant_image').attr('src');
        if (newVariantImage !== optionVariantImage) {
            $('<p>').text('image variant option src changed').insertAfter('.oe_optional_products_modal .js_product:eq(1) .product-name');
        }
    }
}, {
    extra_trigger: '.oe_optional_products_modal .js_product:eq(1) div:contains("image variant option src changed")',
    trigger: '.oe_optional_products_modal .js_product:eq(1) input[data-value_name="Steel"]',
}, {
    trigger: 'li.js_attribute_value span:contains(Aluminium)',
    extra_trigger: '.oe_optional_products_modal',
    run: 'click'
}, {
    trigger: '.oe_price span:contains(22.90)',
    run: function (){}, // check
}, {
    trigger: '.oe_optional_products_modal .js_product:has(strong:contains(Conference Chair)) .js_add',
    extra_trigger: '.oe_optional_products_modal .js_product:has(strong:contains(Conference Chair))',
    run: 'click'
}, {
    trigger: '.oe_optional_products_modal .js_product:has(strong:contains(Chair floor protection)) .js_add',
    extra_trigger: '.oe_optional_products_modal .js_product:has(strong:contains(Chair floor protection))',
    run: 'click'
}, {
    trigger: 'span:contains(1,269.80)',
    run: function (){}, // check
}, {
    trigger: 'button:has(span:contains(Proceed to Checkout))',
    run: 'click',
});

});
