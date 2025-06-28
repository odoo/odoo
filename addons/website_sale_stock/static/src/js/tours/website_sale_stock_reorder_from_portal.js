/** @odoo-module **/

import { registry } from "@web/core/registry";
import { clickOnElement } from '@website/js/tours/tour_utils';

registry.category("web_tour.tours").add('website_sale_stock_reorder_from_portal', {
        url: '/my/orders',
    steps: () => [
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
            run: "click",
            expectUnloadPage: true,
        },
        clickOnElement('Reorder Again', '.o_wsale_reorder_button'),
        {
            content: "Check that there is one out of stock product",
            trigger: "#o_wsale_reorder_body div.text-warning span:contains('This product is out of stock.')",
            run: "click",
        },
        {
            content: "Check that there is one product that does not have enough stock",
            trigger: "#o_wsale_reorder_body div.text-warning:contains('You ask for 2.0 Units but only 1.0 are available.')",
        },
    ]
});
