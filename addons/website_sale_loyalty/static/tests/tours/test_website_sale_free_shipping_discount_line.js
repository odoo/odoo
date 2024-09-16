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
        wsTourUtils.goToCart({ quantity: 3 }),
        wsTourUtils.goToCheckout(),
        {
            content: "select delivery2",
            trigger: "li label:contains(delivery2)",
            run: "click",
        },
        {
            content: "check if delivery price is correct'",
            trigger: "[name=o_delivery_method]:has(label:contains(delivery2)) .oe_currency_value:contains(10.00)",
        },
        {
            content: "confirm shipping method",
            trigger: 'a[href="/shop/confirm_order"]',
            run: "click",
        },
        {
            content: "open cart overview",
            trigger: ".accordion-button",
            run: "click",
        },
        {
            content: "check if delivery price is correct",
            trigger: "#order_delivery .oe_currency_value:contains(10.00)",
        },
        {
            content: "check if shipping discount is correct",
            trigger: "[data-reward-type=shipping] .oe_currency_value:contains(- 6.00)",
        },
        {
            content: "pay with eWallet",
            trigger: "a.btn-primary[role=button]:contains(Pay with eWallet)",
            run: 'click',
        },
        {
            content: "wait for accordion to collapse, then reopen",
            trigger: ".accordion-button.collapsed",
            run: 'click',
        },
        {
            content: "check eWallet discount",
            trigger: "[data-reward-type=discount] .oe_currency_value:contains(- 349.60)",
        },
        {
            content: "select delivery1",
            trigger: "li label:contains(delivery1)",
            run: 'click',
        },
        {
            content: "check for eWallet update after shipping cost change",
            trigger: "[data-reward-type=discount] .oe_currency_value:contains(- 345.00)",
        },
        {
            content: "check if new delivery price is correct",
            trigger: "[name=o_delivery_method]:has(label:contains(delivery1)) .oe_currency_value:contains(5.00)",
        },
        {
            content: "check if new shipping discount is correct",
            trigger: "[data-reward-type=shipping] .oe_currency_value:contains(- 5.00)",
        },
    ],
});
