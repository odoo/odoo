import { registry } from "@web/core/registry";
import { assertCartContains } from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("website_sale.cart_recovery", {
    steps: () => [
        ...assertCartContains({ productName: "Test product" }),
        ...assertCartContains({ productName: "Test Service Product" }),
    ],
});
