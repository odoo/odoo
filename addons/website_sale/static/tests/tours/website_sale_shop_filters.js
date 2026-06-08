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
