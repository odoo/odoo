/** @odoo-module **/

import tour from 'web_tour.tour';
import wsTourUtils from 'website_sale.tour_utils';
import wTourUtils from 'website.tour_utils';


function applyCoupon(couponCode) {
    return [
        {
            content: 'Click on "I have a promo code"',
            extra_trigger: '#cart_products',
            trigger: '.show_coupon',
        },
        {
            content: 'insert gift card code',
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: `text ${couponCode}`,
        },
        wTourUtils.clickOnElement('validate the gift card', 'form[name="coupon_code"] .a-submit'),
    ];
}

tour.register('shop_sale_gift_card', {
        test: true,
        url: '/shop'
    },
    [
        // Add a small drawer to the order (50$)
        ...wsTourUtils.addToCart({productName: 'Small Drawer'}),
        wsTourUtils.goToCart({quantity: 1}),
        ...applyCoupon('GIFT_CARD'),
        {
            content: 'check gift card line',
            trigger: '.td-product_name:contains("PAY WITH GIFT CARD")',
        },
        {
            content: 'check gift card amount',
            trigger: '.oe_currency_value:contains("-﻿50.00")',
            run: function () {
            },
        },
        ...applyCoupon('10PERCENT'),

        {
            content: 'check gift card amount',
            trigger: '.oe_currency_value:contains("-﻿45.00")',
            run: function () {
            },
        },
        ...wsTourUtils.addToCart({productName: 'TEST - Gift Card'}),
        wsTourUtils.goToCart({quantity: 2}),
    ],
);

