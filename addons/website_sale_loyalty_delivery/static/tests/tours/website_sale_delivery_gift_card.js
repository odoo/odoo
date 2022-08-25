odoo.define('website_sale_loyalty_giftcard.test', function (require) {
    'use strict';

    require("website_sale.tour");
    var tour = require("web_tour.tour");
    const tourUtils = require('website_sale.tour_utils');

    tour.register('shop_sale_loyalty_delivery', {
        test: true,
        url: '/shop?search=Accoustic',
    },
        [
            {
                content: "select Small Cabinet",
                trigger: '.oe_product a:contains("Acoustic Bloc Screens")',
            },
            {
                content: "add 1 Small Cabinet into cart",
                trigger: '#product_details input[name="add_qty"]',
                run: "text 1",
            },
            {
                content: "click on 'Add to Cart' button",
                trigger: "a:contains(ADD TO CART)",
            },
            tourUtils.goToCart(1),
            {
                content: "go to checkout",
                trigger: 'a[href="/shop/checkout?express=1"]',
                run: 'click'
            },
            {
                content: "select delivery method 1",
                trigger: "li label:contains(delivery1)",
                run: 'click'
            },
            {
                content: "click on 'Pay with gift card'",
                trigger: '.show_coupon',
                run: 'click'
            },
            {
                content: "Enter gift card code",
                trigger: "form[name='coupon_code'] input[name='promo']",
                run: 'text 123456'
            },
            {
                content: "click on 'Pay'",
                trigger: "a[role='button'].a-submit:contains(Apply)",
                run: 'click'
            },
            {
                content: "check if delivery price is correct'",
                trigger: "#order_delivery .oe_currency_value:contains(5.00)",
                run: () => {} // this is a check
            },
            {
                content: "check if total price is correct",
                trigger: "tr#order_total span.oe_currency_value:contains(0.00)",
                run: () => {} // this is a check
            },
        ]
    );
});
