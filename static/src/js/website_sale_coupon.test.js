odoo.define('website_sale_coupon.test', function (require) {
'use strict';

require("website_sale.tour");
var tour = require("web_tour.tour");
var base = require("web_editor.base");

tour.register('shop_sale_coupon', {
    test: true,
    url: '/shop?search=Large%20Cabinet',
    wait_for: base.ready()
},
    [
        /* 1. Buy 1 Large Cabinet, enable coupon code & insert 10% code */
        {
            content: "select Large Cabinet",
            trigger: '.oe_product_cart a:contains("Large Cabinet")',
        },
        {
            content: "add 3 Large Cabinet into cart",
            trigger: '#product_details input[name="add_qty"]',
            run: "text 3",
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: "a:contains(Add to Cart)",
        },
        {
            content: "open customize menu",
            extra_trigger: '.oe_website_sale .oe_cart',
            trigger: '#customize-menu > a',
        },
        {
            content: "enable 'Promo Code' if needed",
            trigger: "#customize-menu a:contains(Promo Code)",
            run: function () {
                if (!$('#customize-menu a:contains(Promo Code) input').prop('checked')) {
                    $('#customize-menu a:contains(Promo Code)').click();
                }
            }
        },
        {
            content: "click on 'I have a promo code'",
            extra_trigger: '.show_coupon',
            trigger: '.show_coupon',
        },
        {
            content: "insert promo code '10pc'",
            extra_trigger: 'form[name="coupon_code"]',
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: "text 10pc",
        },
        {
            content: "validate the coupon",
            trigger: 'form[name="coupon_code"] .a-submit',
        },
        {
            content: "check reward product",
            trigger: '.reward_product:contains("10.0% discount on total amount")',
            run: function () {}, // it's a check
        },
        /* 2. Add some cabinet to get a free one, play with quantity */
        {
            content: "add more Large Cabinet into cart",
            trigger: '#cart_products input.js_quantity',
            run: "text 4",
        },
        {
            content: "check reduction amount got recomputed",
            extra_trigger: '.oe_currency_value:contains("96.00")', // For some reason, "-96.00" won't work
            trigger: '.reward_product:contains("Free Product - Large Cabinet")',
            run: function () {}, // it's a check
        },
        {
            content: "remove one cabinet from cart",
            trigger: '#cart_products a.js_add_cart_json:first',
        },
        {
            content: "check free product is removed",
            trigger: '#wrap:not(:has(.reward_product:contains("Free Product - Large Cabinet")))',
            run: function () {}, // it's a check
        },
        /* 3. Empty cart and disable coupon */
        {
            content: "remove Large Cabinet from cart",
            trigger: '#cart_products input.js_quantity:first',
            run: "text 0",
        },
        {
            content: "check cart is empty",
            trigger: '#wrap:not(:has(#cart_products))',
            run: function () {}, // it's a check
        },
        {
            content: "check cart is empty (2)",
            trigger: 'div.js_cart_lines:contains(Your cart is empty!)',
            run: function () {}, // it's a check
        },
        /* 4. Disabled customize options coupon box & 'Show # found'*/
        {
            content: "open customize menu",
            extra_trigger: '.oe_website_sale .oe_cart',
            trigger: '#customize-menu > a',
        },
        {
            content: "click on 'Promo Code'",
            trigger: "#customize-menu a:contains(Promo Code)",
        },
        {
            content: "click on 'Continue Shopping'",
            trigger: "a:contains(Continue Shopping)",
        },
    ]
);
});
