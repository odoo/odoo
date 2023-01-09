odoo.define("website_sale_product_TESTurator.tour_shop_custom_attribute_value", function (require) {
"use strict";

var tour = require('web_tour.tour');
var optionVariantImage;

tour.register("a_shop_custom_attribute_value", {
    url: "/shop?search=Customizable Desk",
    test: true,
}, [{
        content: "click on Customizable Desk",
        trigger: '.oe_product_cart a:contains("Customizable Desk (TEST)")',
}, {
    trigger: 'a.js_add_cart_json:has(i.fa-plus)',
    run: 'click',
}, {
    trigger: 'span.text-danger span:contains(750)',
    run: function (){}, // check
}, {
    trigger: 'span.oe_price span:contains(600)',
    run: function (){}, // check
}, {
    id: 'add_cart_step',
    trigger: 'a:contains(ADD TO CART)',
    run: 'click',
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
    trigger: '.oe_price span:contains(22.90)',
    run: function (){}, // check
}, {
    trigger: '.oe_advanced_configurator_modal .js_product:has(strong:contains(Conference Chair)) .js_add',
    extra_trigger: '.oe_advanced_configurator_modal .js_product:has(strong:contains(Conference Chair))',
    run: 'click'
}, {
    trigger: '.oe_advanced_configurator_modal .js_product:has(strong:contains(Chair floor protection)) .js_add',
    extra_trigger: '.oe_advanced_configurator_modal .js_product:has(strong:contains(Chair floor protection))',
    run: 'click'
}, {
    trigger: 'span:contains(1,257.00)',
    run: function (){}, // check
}, {
    trigger: 'button:has(span:contains(Proceed to Checkout))',
    run: 'click',
}]);

});
