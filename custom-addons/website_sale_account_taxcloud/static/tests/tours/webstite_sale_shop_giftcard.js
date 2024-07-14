/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('shop_sale_giftcard', {
    test: true,
    url: '/shop',
    steps: () => [
        ...tourUtils.addToCart({productName: "Acoustic Bloc Screens"}),
        tourUtils.goToCart(1),
        tourUtils.goToCheckout(),
        {
            content: "click on 'Pay with gift card'",
            trigger: '.show_coupon',
            extra_trigger: 'button[name="o_payment_submit_button"]',
            run: 'click'
        },
        {
            content: "Enter gift card code",
            trigger: "input[name='promo']",
            run: 'text 123456'
        },
        {
            content: "click on 'Pay'",
            trigger: "button[type='submit'].a-submit:contains(Pay)",
            run: 'click'
        },
        ...tourUtils.assertCartAmounts({
            total: '0.00',
        }),
    ]
});
