/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("shop_checkout_address_ec", {
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({ productName: "Test Product" }),
        tourUtils.goToCart({ quantity: 1 }),
        {
            content: "Go to checkout",
            trigger: "a:contains('Checkout')",
            run: "click",
        },
        {
            content: "Check that VAT field is present",
            trigger: "label:contains('Identification Type')",
        },
        {
            content: "Check that VAT field is present",
            trigger: "label:contains('Identification Number')",
        },
    ],
});

registry.category("web_tour.tours").add("tour_new_billing_ec", {
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({ productName: "Test Product" }),
        tourUtils.goToCart({ quantity: 1 }),
        {
            content: "Go to checkout",
            trigger: "a:contains('Checkout')",
            run: "click",
        },
        {
            content: "Fill vat",
            trigger: "#o_vat",
            run: "fill 111111111111",
        },
        {
            content: "Save address",
            trigger: "button#save_address",
            run: "click",
        },
        {
            content: "Billing address is not same as delivery address",
            trigger: '#use_delivery_as_billing',
            run: "click",
        },
        {
            content: "Add new billing address",
            trigger: '.all_billing a[href^="/shop/address?address_type=billing"]:contains("Add address")',
            run: "click",
        },
        ...tourUtils.fillAdressForm(),
        {
            content: "Save address",
            trigger: "button#save_address",
            run: "click",
        },
    ],
});
