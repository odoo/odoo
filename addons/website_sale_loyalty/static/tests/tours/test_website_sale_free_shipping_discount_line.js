/** @odoo-module **/

import { registry } from "@web/core/registry";
import wsTourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('check_shipping_discount', {
    test: true,
    url: '/shop?search=Plumbus',
    steps: () => [
        {
            content: "select Plumbus",
            trigger: '.oe_product a:contains("Plumbus")',
        },
        {
            content: "add 3 Plumbus into cart",
            trigger: '#product_details input[name="add_qty"]',
            run: "text 3",
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
        },
        wsTourUtils.goToCart({quantity: 3}),
        {
            content: "go to checkout",
            trigger: 'a[href="/shop/checkout?express=1"]',
        },
        {
            content: "select delivery with rule",
            trigger: 'li label:contains("delivery with rule")',
        },
        {
            trigger: ".accordion-button"
        },
        {
            content: "check if delivery price is correct'",
            trigger: 'label:contains("delivery with rule") + span.o_wsale_delivery_badge_price:contains(100.00)',
            isCheck: true,
        },
        {
            content: "check if delivery price is correct'",
            trigger: "#order_delivery .oe_currency_value:contains(100.00)",
            isCheck: true,
        },
        {
            content: "check if delivery price is correct'",
            trigger: "[data-reward-type='shipping'] .oe_currency_value:contains('-﻿75.00')",
            isCheck: true,
        },
    ],
});
