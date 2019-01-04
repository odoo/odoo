odoo.define("website_sale.tour_shop_custom_attribute_value", function (require) {
    "use strict";

    var tour = require("web_tour.tour");
    var base = require("web_editor.base");

    tour.register("shop_custom_attribute_value", {
        url: "/shop",
        test: true,
        wait_for: base.ready()
    }, [{
        trigger: 'img[src*="/product.product/10"]',
        run: 'click'
    }, {
        trigger: 'li.js_attribute_value span:contains(Custom)',
        extra_trigger: 'li.js_attribute_value',
        run: 'click',
    }, {
        trigger: 'input.variant_custom_value',
        run: 'text Wood',
    }, {
        trigger: 'a:contains(Add to Cart)',
        run: 'click',
    }, {
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
    }, {
        trigger: 'span:contains(Custom: Wood)',
        extra_trigger: '#cart_products',
        run: function (){}, // check
    }]);
});
