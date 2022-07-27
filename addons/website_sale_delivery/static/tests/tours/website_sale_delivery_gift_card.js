odoo.define('website_sale_delivery.test', function (require) {
    'use strict';

    require("website_sale.tour");
    var tour = require("web_tour.tour");
    const tourUtils = require('website_sale.tour_utils');

    tour.register('shop_sale_giftcard_delivery', {
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
                content: "select free delivery method",
                trigger: "li label:contains(delivery1)",
                run: 'click'
            },
            {
                content: "click on 'Pay with gift card'",
                trigger: '.js_show_gift_card',
                run: 'click'
            },
            {
                content: "Enter gift card code",
                trigger: "input[name='promo']",
                run: 'text 044c-7c9c-432f-810e-dcff'
            },
            {
                content: "click on 'Pay'",
                trigger: "button[type='submit'].a-submit:contains(Pay)",
                run: 'click'
            },
            {
                content: "check if delivery price is correct'",
                trigger: "#order_delivery .oe_currency_value:contains(5.00)",
            },
        ]
    );
});
