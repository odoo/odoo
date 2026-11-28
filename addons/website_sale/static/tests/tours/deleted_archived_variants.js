import { registry } from "@web/core/registry";
import { pickPills } from "@website_sale/js/tours/tour_utils";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add("website_sale.deleted_archived_variants", {
    steps: () => [
        {
            content: "check price on /shop (template price)",
            trigger: '.oe_product_cart .oe_currency_value:contains("1.00")',
            run: "click",
        },
        {
            content: "select Test Product 2",
            trigger: ".oe_product_cart a:text(Test Product 2)",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "check price (3rd variant)",
            trigger: '.oe_currency_value:contains("31.00")',
            run: "click",
        },
        pickPills("My Value 2"),
        pickPills("My Value 3"),
        {
            content: "check price (3rd variant)",
            trigger: '.oe_currency_value:contains("31.00")',
            run: "click",
        },
        pickPills("My Value 1"),
        {
            content: "check add to cart not possible",
            trigger: '.js_product button[name="add_to_cart"]:disabled',
        },
    ],
});
