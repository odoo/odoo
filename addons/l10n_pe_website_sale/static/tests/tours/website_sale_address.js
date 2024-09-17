/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('update_the_address_for_peru_company', {
    test: true,
    url: '/shop',
    steps: () => [
        ...tourUtils.addToCart({ productName: "Test Product" }),
        tourUtils.goToCart({ quantity: 1 }),
        tourUtils.goToCheckout(),
        {
            content: "Edit billing/shipping address",
            trigger: "#shipping_and_billing a:contains('Edit')",
        },
        {
            content: "Edit the first address",
            trigger: "div.all_billing div.card a:contains('Edit')",
        },
        {
            content: "Check that Company Name field exists",
            trigger: "input[name='company_name']",
        },
        {
            content: "Check that identification type field exists",
            trigger: "label:contains('Identification Type')",
        },
        {
            content: "Check that identification number field exists",
            trigger: "input[name='vat']",
        },
    ],
});
