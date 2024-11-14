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
            trigger: 'a.btn-primary:contains(Pay with eWallet)',
            run: 'click',
        },
        wsTourUtils.goToCheckout(),
        {
            content: "select delivery1",
            trigger: 'li label:contains(delivery1)',
            run: 'click',
        },
        {
            content: "check delivery is free due to total being over $75.00",
            trigger: '#order_delivery .oe_currency_value:contains(0.00)',
        },
        {
            content: "enter discount code",
            trigger: 'form[name=coupon_code] input',
            run: 'edit test-50pc',
        },
        {
            content: "apply discount code",
            trigger: 'form[name=coupon_code] .a-submit',
            run: 'click',
        },
        {
            content: "check delivery cost was updated due to total being under $75.00",
            trigger: '#order_delivery .oe_currency_value:contains(5.00)',
        },
    ],
});
