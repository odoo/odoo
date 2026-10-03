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
            trigger: "div.alert-warning:contains('Some products became unavailable and your cart has been updated. We're sorry for the inconvenience.')",
        },
        {
            content: "Check that there is one product that does not have enough stock",
            trigger: "div.o_cart_product i.fa.fa-warning[title='You ask for 2 partially_available_product but only 1 is available']",
        },
    ]
});
