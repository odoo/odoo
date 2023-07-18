/** @odoo-module alias=website_sale_loyalty_giftcard.test **/

import { registry } from "@web/core/registry";
import wsTourUtils from "website_sale.tour_utils";

registry.category("web_tour.tours").add('shop_sale_loyalty_delivery', {
    test: true,
    url: '/shop',
    steps: [
        ...wsTourUtils.addToCart({productName: "Acoustic Bloc Screens"}),
        wsTourUtils.goToCart(),
        wsTourUtils.goToCheckout(),
        {
            content: "select delivery method 1",
            trigger: "li label:contains(delivery1)",
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
            trigger: "#order_total span.oe_currency_value:contains(0.00)",
            run: () => {} // this is a check
        },
    ]
});
