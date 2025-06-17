import { registry } from "@web/core/registry";
import { clickOnElement } from '@website/js/tours/tour_utils';

registry.category("web_tour.tours").add('website_sale_stock_reorder_from_portal', {
        url: '/my/orders',
    steps: () => [
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
            run: "click",
        },
        clickOnElement('Reorder Again', '.o_wsale_reorder_button'),
        {
            content: "Check that there is one out of stock product",
            trigger: "div.alert-warning:contains('1.0 unavailable_product was not added to your cart because it is currently unavailable.')",
        },
        {
            content: "Check that there is one product that does not have enough stock",
            trigger: "div.alert-warning:contains('Only 1.0 partially_available_product is available. It has been added to your cart.')",
        },
    ]
});
