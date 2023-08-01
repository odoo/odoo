/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('shop_sale_gift_card', {
    test: true,
    url: '/shop',
    steps: () => [
        // Add a small drawer to the order (50$)
        ...tourUtils.addToCart({productName: "TEST - Small Drawer"}),
        tourUtils.goToCart(),
        {
            content: 'Click on "I have a promo code"',
            extra_trigger: '#cart_products',
            trigger: '.show_coupon',
        },
        {
            content: 'insert gift card code',
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: 'text GIFT_CARD'
        },
        {
            content: 'validate the gift card',
            trigger: 'form[name="coupon_code"] .a-submit',
        },
        {
            content: 'check gift card line',
            trigger: '.td-product_name:contains("PAY WITH GIFT CARD")',
        },
        {
            content: 'Click on "I have a promo code"',
            trigger: '.show_coupon',
        },
        {
            content: 'insert gift card code',
            extra_trigger: 'form[name="coupon_code"]',
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: 'text 10PERCENT'
        },
        {
            content: 'validate the gift card',
            trigger: 'form[name="coupon_code"] .a-submit',
        },
        {
            content: 'check gift card amount',
            trigger: '.oe_website_sale .oe_cart',
            run: function () {}, // it's a check
        },
        ...tourUtils.addToCart({productName: "TEST - Gift Card"}),
        tourUtils.goToCart({quantity: 2}),
        {
            content: 'check gift card amount',
            trigger: '.oe_website_sale .oe_cart',
            run: function () {}, // it's a check
        },
    ],
});
