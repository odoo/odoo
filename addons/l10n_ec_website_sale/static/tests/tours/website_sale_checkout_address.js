/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("shop_checkout_address_ec", {
    test: true,
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({ productName: "Test Product" }),
        tourUtils.goToCart({ quantity: 1 }),
        {
            content: "Go to checkout",
            trigger: "a:contains('Checkout')",
        },
        {
            content: "Check that VAT field is present",
            trigger: "label:contains('Identification Type')",
            isCheck: true,
        },
        {
            content: "Check that VAT field is present",
            trigger: "label:contains('Identification Number')",
            isCheck: true,
        },
    ],
});
