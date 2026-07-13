/** @odoo-module **/

import { registry } from '@web/core/registry';
import wsTourUtils from '@website_sale/js/tours/tour_utils';

registry.category('web_tour.tours').add('update_shipping_after_discount', {
    url: "/shop",
    test: true,
    checkDelay: 250,
    steps: () => [
        ...wsTourUtils.addToCart({ productName: "Plumbus" }),
        wsTourUtils.goToCart(),
        {
            content: "use eWallet to check it doesn't impact `free_over` shipping",
            trigger: 'form[name=coupon_code] input',
            run: 'text infinite-money-glitch',
        },
        {
            content: "apply eWallet code",
            trigger: 'form[name=coupon_code] .a-submit',
        },
        wsTourUtils.goToCheckout(),
        {
            content: "select delivery1",
            trigger: 'li label:contains(delivery1)',
        },
        {
            content: "check delivery is free due to total being over $75.00",
            trigger: '#order_delivery .oe_currency_value:contains(0.00)',
            isCheck: true,
        },
        {
            content: "enter discount code",
            trigger: 'form[name=coupon_code] input',
            run: 'text test-50pc',
        },
        {
            content: "apply discount code",
            trigger: 'form[name=coupon_code] .a-submit',
        },
        {
            content: "check delivery cost was updated due to total being under $75.00",
            trigger: '#order_delivery .oe_currency_value:contains(5.00)',
            isCheck: true,
        },
    ],
});
