/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('check_shipping_discount', {
    url: '/shop?search=Plumbus',
    checkDelay: 50,
    steps: () => [
        {
            content: "select Plumbus",
            trigger: '.oe_product a:contains("Plumbus")',
            run: "click",
        },
        {
            content: "add 3 Plumbus into cart",
            trigger: '#product_details input[name="add_qty"]',
            run: "edit 3",
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
            run: "click",
        },
        wsTourUtils.goToCart({quantity: 3}),
        {
            content: "go to checkout",
            trigger: 'a[name="website_sale_main_button"]',
            run: "click",
        },
        {
            content: "select delivery with rule",
            trigger: 'li label:contains("delivery with rule")',
            run: "click",
        },
        {
            content: "check if delivery price is correct'",
            trigger: "[name='o_delivery_method']:has(.o_delivery_carrier_label:contains('delivery with rule')) span.o_wsale_delivery_price_badge .oe_currency_value:contains(100.00)",
        },
        {
            content: "confirm shipping method",
            trigger: 'a[href="/shop/confirm_order"]',
            run: "click",
        },
        {
            trigger: ".oe_cart:contains(confirm order)",
        },
        {
            trigger: ".o_total_card:contains(order summary)",
        },
        {
            trigger: ".o_total_card button.accordion-button",
            run: "click",
        },
        {
            content: "check if delivery price is correct'",
            trigger: "#order_delivery .oe_currency_value:contains(100.00)",
        },
        {
            content: "check if delivery price is correct'",
            trigger: "[data-reward-type='shipping'] .oe_currency_value:contains('- 75.00')",
        },
    ],
});
