import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("shop_attribute_filters_remain_when_changing_page", {
    steps: () => [
        {
            content: "Select first attribute value",
            trigger: ".products_attributes_filters form.js_attributes input:eq(0)",
            run: "click",
        },
        {
            content: "Check that the first filter is applied",
            trigger: "li.active a.page-link[href*='size']",
        },
        {
            content: "Select last attribute value",
            trigger: ".products_attributes_filters form.js_attributes input:eq(3)",
            run: "click",
        },
        {
            content: "Check that the second filter is applied",
            trigger: "li.active a.page-link[href*='color']",
        },
        {
            content: "Select page 2",
            trigger: 'li a.page-link:contains("2")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "First attribute value should be checked",
            trigger: ".products_attributes_filters form.js_attributes input:eq(0):checked",
        },
        {
            content: "Last attribute value should be checked",
            trigger: ".products_attributes_filters form.js_attributes input:eq(3):checked",
        },
    ],
});

registry.category("web_tour.tours").add("shop_attribute_value_grouping", {
    steps: () => [
        {
            content: "Check that the parent value is displayed",
            trigger: '.products_attributes_filters label:contains("Black")',
        },
        {
            content: "Select the parent value",
            trigger: '.products_attributes_filters label:contains("Black")',
            run: "click",
        },
        {
            content: "Check that products matching the Grey child are displayed",
            trigger: '.oe_product:has(.o_wsale_products_item_title:contains("Grouped Grey Product")',
        },
        {
            content: "Check that unrelated products are not displayed",
            trigger: '#o_wsale_products_grid:not(:has(article[aria-label="Standalone Red Product"]))',
        },
    ],
});
