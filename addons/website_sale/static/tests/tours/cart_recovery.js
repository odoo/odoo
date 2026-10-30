import { registry } from "@web/core/registry";
import { assertCartContains } from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("website_sale.cart_recovery", {
    steps: () => [
        {
            content: "The cart should be empty",
            trigger: "h5:contains('Your cart is empty!')",
        },
        {
            content: "The cart page should have cart recovery options",
            trigger: 'p:contains("This is your current cart")',
        },
        {
            content: "check the page is working, click on restore",
            trigger: 'p:contains("restore") a:contains("Click here")',
            run: "click",
            expectUnloadPage: true,
        },
        ...assertCartContains({ productName: "Test product" }),
        ...assertCartContains({ productName: "Test Service Product" }),
    ],
});
