import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_customer_display", {
    steps: () => [
        {
            content: "Check that the Customer Display is initialized and ready",
            trigger: ".o_customer_display div:contains('Welcome')",
        },
    ],
});
