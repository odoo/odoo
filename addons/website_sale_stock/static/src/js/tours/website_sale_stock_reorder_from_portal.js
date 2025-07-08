import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('website_sale_stock_reorder_from_portal', {
        url: '/my/orders',
    steps: () => [
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Reorder Again",
            trigger: '.o_wsale_reorder_button',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check that there is one out of stock product",
            trigger: "div.alert-warning:contains('\"1.0 unavailable_product\" couldn't be added to your cart because it's currently unavailable.')",
        },
        {
            content: "Check that there is one product that does not have enough stock",
            trigger: "div.alert-warning:contains('Only \"1.0 partially_available_product\" available and added to your cart.')",
        },
    ]
});
