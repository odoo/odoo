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
            extra_trigger: '#delivery_carrier label:containsExact("Delivery Now Free Over 10")',
            trigger: "#delivery_carrier span:contains('Free')",
        },
        // Part 2: check multiple delivery & price loaded asynchronously
        {
            content: "Ensure price was loaded asynchronously",
            extra_trigger: '#delivery_carrier input[name="delivery_type"]:checked',
            trigger: '#delivery_method .o_delivery_carrier_select:contains("The Poste")',
            run: "click",
        },
        {
            content: "Select `Wire Transfer` payment method",
            trigger: 'input[name="o_payment_radio"][data-payment-method-code="wire_transfer"]',
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
