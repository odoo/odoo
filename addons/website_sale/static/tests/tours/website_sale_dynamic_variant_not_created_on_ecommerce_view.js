/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_sale_dynamic_variant_not_created_on_ecommerce_view", {
    test: true,
    url: "/shop?search=T-Shirt Dynamic Tour",
    steps: () => [
        {
            content: "Open the dynamic product",
            trigger: '.oe_product_cart a:containsExact("T-Shirt Dynamic Tour")',
        },
        {
            content: "Select color red",
            trigger: 'input[data-attribute_name="Test Color Dynamic"][data-value_name="Red"]',
            run: "click",
        },
        {
            content: "Check color red selected",
            trigger: 'input[data-attribute_name="Test Color Dynamic"][data-value_name="Red"]:propChecked',
            isCheck: true,
        }
    ],
});
