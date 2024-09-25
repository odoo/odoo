/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('shop_sale_gift_card', {
    test: true,
    url: '/shop',
    steps: () => [
        // Add a small drawer to the order (50$)
        ...tourUtils.addToCart({productName: "TEST - Small Drawer"}),
        tourUtils.goToCart(),
        {
            content: 'insert gift card code',
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: "edit GIFT_CARD",
        },
        {
            content: 'validate the gift card',
            trigger: 'form[name="coupon_code"] .a-submit',
            run: "click",
        },
        {
            content: 'check gift card line',
            trigger: "#cart_products div>strong:contains(PAY WITH GIFT CARD)",
        },
        {
            content: "Insert promo",
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: "edit 10PERCENT",
        },
        {
            content: "Validate the promo",
            trigger: 'form[name="coupon_code"] .a-submit',
            run: "click",
        },
        {
            content: "Check promo",
            trigger: "#cart_products div>strong:contains(10% on your order)",
        },
        {
            content: "Click on Continue Shopping",
            trigger: "div.card-body a:contains(Continue shopping)",
            run: "click",
        },
        ...tourUtils.addToCart({productName: "TEST - Gift Card"}),
        tourUtils.goToCart({quantity: 2}),
    ],
});
