/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("test_validate_additional_fields", {
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
            content: "Confirm Address",
            trigger: "a:contains('Confirm')",
        },
        {
            content: "Check that the additional field page is open",
            trigger: "h3:contains('Required additional fields')",
            isCheck: true,
        },
        {
            content: "Check no need invoice",
            trigger: "input[name='need_invoice'][value=0]",
        },
        {
            content: "Click Next",
            trigger: "a.a-submit:contains('Continue checkout')",
        },
        {
            content: "Check we are on confirm order page",
            trigger: "#address_on_payment",
            isCheck: true,
        },
    ],
});
