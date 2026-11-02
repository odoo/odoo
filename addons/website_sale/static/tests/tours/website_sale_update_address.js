import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('update_billing_shipping_address', {
    url: '/shop',
    steps: () => [
        ...tourUtils.addToCart({ productName: "Office Chair Black TEST", expectUnloadPage: true }),
        tourUtils.goToCart({quantity: 1}),
        tourUtils.goToCheckout(),
        tourUtils.confirmOrder(),
        {
            content: "Edit Address",
            trigger: '#delivery_and_billing a:contains("Edit")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Edit  billing address which is shipping address too",
            trigger: 'a.js_edit_address',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Empty the phone field",
            trigger: 'input[name="phone"]',
            run: "clear",
        },
        {
            content: "Save address",
            trigger: "a[name='website_sale_main_button']",
            run: "click",
        },
        {
            content: "Check there is a warning for required field.",
            trigger: ':invalid',
        },
    ],
});

registry.category("web_tour.tours").add("website_sale_line_price_after_delivery_address_change", {
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({ productName: "Fiscal Product", expectUnloadPage: true }),
        tourUtils.goToCart({ quantity: 1 }),
        tourUtils.goToCheckout(),
        {
            content: "Check the line price with the foreign tax",
            trigger: ".o_total_card td[name=website_sale_cart_summary_line_price]:contains(120.00)",
        },
        {
            content: "Wait for the delivery methods to be loaded",
            trigger: "#o_delivery_form:not(:has(.fa-spin))",
        },
        {
            content: "Wait for the checkout to be ready",
            trigger: "[name=website_sale_main_button]:not(.disabled)",
        },
        {
            content: "Select the domestic delivery address",
            trigger: '.card[data-address-type="delivery"]:contains(Domestic Street)',
            run: "click",
        },
        {
            content: "Check the line price is updated with the domestic tax",
            trigger: ".o_total_card td[name=website_sale_cart_summary_line_price]:contains(121.00)",
        },
        {
            content: "Wait for the delivery methods to be loaded",
            trigger: "#o_delivery_form:not(:has(.fa-spin))",
        },
        {
            content: "Wait for the checkout to be ready",
            trigger: "[name=website_sale_main_button]:not(.disabled)",
        },
        {
            content: "Select the foreign delivery address",
            trigger: '.card[data-address-type="delivery"]:contains(Foreign Street)',
            run: "click",
        },
        {
            content: "Check the line price is updated with the foreign tax",
            trigger: ".o_total_card td[name=website_sale_cart_summary_line_price]:contains(120.00)",
        },
    ],
});
