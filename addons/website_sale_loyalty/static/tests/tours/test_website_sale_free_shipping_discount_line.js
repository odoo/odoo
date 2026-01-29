/** @odoo-module **/

import { registry } from "@web/core/registry";
import wsTourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("check_shipping_discount", {
    test: true,
    url: "/shop?search=Plumbus",
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
        wsTourUtils.goToCart({ quantity: 3 }),
        wsTourUtils.goToCheckout(),
        {
            content: "select delivery1",
            trigger: "li label:contains(delivery1)",
        },
        {
            trigger: ".accordion-button",
        },
        {
            content: "check if delivery price is correct'",
            trigger: "label:contains(delivery1) + span[name=price]:contains(100.00)",
            isCheck: true,
        },
        {
            content: "check if delivery price is correct'",
            trigger: "#order_delivery .oe_currency_value:contains(100.00)",
            isCheck: true,
        },
        {
            content: "check if shipping discount is correct",
            trigger: "[data-reward-type='shipping'] .oe_currency_value:contains('-﻿75.00')",
            isCheck: true,
        },
        {
            content: "enter eWallet code",
            trigger: "form[name=coupon_code] input",
            run: "text infinite-money-glitch",
        },
        {
            trigger: "form[name=coupon_code] .a-submit",
        },
        {
            content: "wait for accordion to collapse, then reopen",
            trigger: ".accordion-button.collapsed",
        },
        {
            content: "check eWallet discount",
            trigger: "[data-reward-type=discount] .oe_currency_value:contains(325.00)",
            isCheck: true,
        },
        {
            content: "select delivery2",
            trigger: "li label:contains(delivery2)",
        },
        {
            content: "check for eWallet update after shipping cost change",
            trigger: "[data-reward-type=discount] .oe_currency_value:contains(300.00)",
            isCheck: true,
        },
        {
            content: "check if new delivery price is correct'",
            trigger: "label:contains(delivery2) + span[name=price]:contains(10.00)",
            isCheck: true,
        },
        {
            content: "check if new shipping discount is correct'",
            trigger: "[data-reward-type=shipping] .oe_currency_value:contains(-﻿10.00)",
            isCheck: true,
        },
    ],
});
