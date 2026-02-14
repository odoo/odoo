import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("shop_attribute_filters_remain_when_changing_page", {
    url: "/shop",
    steps: () => [
        {
            content: "Select first attribute value",
            trigger: ".products_attributes_filters form.js_attributes input:eq(0)",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Select last attribute value",
            trigger: ".products_attributes_filters form.js_attributes input:eq(3)",
            run: "click",
            expectUnloadPage: true,
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
