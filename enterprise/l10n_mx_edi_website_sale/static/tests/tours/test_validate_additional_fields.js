/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("test_validate_additional_fields", {
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({ productName: "Test Product", expectUnloadPage: true }),
        tourUtils.goToCart({ quantity: 1 }),
        {
            content: "Go to checkout",
            trigger: "a:contains('Checkout')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Confirm Address",
            trigger: "a:contains('Confirm')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check that the additional field page is open",
            trigger: "h3:contains('Required additional fields')",
        },
        {
            content: "Check no need invoice",
            trigger: `input[name="need_invoice"][value="0"]`,
            run: "click",
        },
        {
            content: "Click Next",
            trigger: "a.a-submit:contains('Continue checkout')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check we are on confirm order page",
            trigger: "#address_on_payment",
        },
    ],
});
