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

registry.category("web_tour.tours").add("checkout_change_address_then_select_delivery", {
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({ productName: "Test Product", expectUnloadPage: true }),
        tourUtils.goToCart({quantity: 1}),
        tourUtils.goToCheckout(),
        {
            content: "Select the US address (no delivery available)",
            trigger: '.o_address_kanban_card address:contains("United State")',
            run: "click",
        },
        {
            content: "Confirm address selection",
            trigger: 'a[name="website_sale_main_button"]',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Go back to address step",
            trigger: 'a:has(span:contains("Back to address"))',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Select the Australian delivery address",
            trigger: '.o_address_kanban_card address:contains("Australia")',
            run: "click",
        },
        {
            content: "Select an available delivery method",
            trigger: "li label:contains(Test carrier)",
            run: "click",
        },
        {
            content: "Click on Confirm button",
            trigger: 'a[name="website_sale_main_button"]',
            run: "click",
            expectUnloadPage: true,
        },
    ],
});
