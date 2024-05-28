/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('check_free_delivery', {
    test: true,
    url: '/shop',
    steps: () => [
        // Part 1: Check free delivery
        ...tourUtils.addToCart({productName: "Office Chair Black TEST"}),
        tourUtils.goToCart({quantity: 1}),
        tourUtils.goToCheckout(),
        {
            content: "Check Free Delivery value to be zero",
            extra_trigger: "#o_delivery_methods label:contains(/^Delivery Now Free Over 10$/)",
            trigger: "#o_delivery_methods span:contains('0.0')",
            run: "click",
        },
        // Part 2: check multiple delivery & price loaded asynchronously
        {
            content: "Ensure price was loaded asynchronously",
            extra_trigger: '#o_delivery_methods input[name="o_delivery_radio"]:checked',
            trigger: '#o_delivery_methods [name="o_delivery_method"]:contains("20.0"):contains("The Poste")',
            run: function () {}, // it's a check
        },
        tourUtils.confirmOrder(),
        {
            content: "Select `Wire Transfer` payment method",
            trigger: 'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]',
            run: "click",
        },
        tourUtils.pay(),
        {
            content: "Confirmation page should be shown",
            trigger: '#oe_structure_website_sale_confirmation_1',
            allowInvisible: true,
            run: function () {}, // it's a check
        }
    ],
});
