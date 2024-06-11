/** @odoo-module **/

import { registry } from "@web/core/registry";
import wsTourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('shop_sale_loyalty_delivery', {
    test: true,
    url: '/shop',
    steps: () => [
        ...wsTourUtils.addToCart({productName: "Acoustic Bloc Screens"}),
        wsTourUtils.goToCart(1),
        wsTourUtils.goToCheckout(),
        {
            content: "select delivery method 1",
            trigger: "li label:contains(delivery1)",
        },
        {
            content: "Enter gift card code",
            trigger: "form[name='coupon_code'] input[name='promo']",
            run: 'text 123456'
        },
        {
            content: "click on 'Pay'",
            trigger: "a[role='button'].a-submit:contains(Apply)",
        },
        ...wsTourUtils.assertCartAmounts({
            total: '0.00',
            delivery: '5.00'
        }),
    ]
});
