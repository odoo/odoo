/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("shop_checkout_address_uy", {
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({ productName: "Test Product" , expectUnloadPage: true }),
        tourUtils.goToCart({ quantity: 1 }),
        {
            content: "Go to checkout",
            trigger: "a:contains('Checkout')",
            run: "click",
        },
        {
            content: "Check that Id type field is present",
            trigger: "label:contains('Identification Type')",
        },
        {
            content: "Check that VAT field is present",
            trigger: "label:contains('Identification Number')",
        },
    ],
});
