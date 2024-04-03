/** @odoo-module **/

import tour from 'web_tour.tour';
import wTourUtils from 'website.tour_utils';

tour.register('website_sale_stock_reorder_from_portal', {
        test: true,
        url: '/my/orders',
    },
    [
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
        },
        wTourUtils.clickOnElement('Reorder Again', '.o_wsale_reorder_button'),
        {
            content: "Check that there is one out of stock product",
            trigger: "#o_wsale_reorder_body div.text-warning span:contains('This product is out of stock.')",
        },
        {
            content: "Check that there is one product that does not have enough stock",
            trigger: "#o_wsale_reorder_body div.text-warning:contains('You ask for 2.0 Units but only 1.0 are available.')",
        },
    ]
);

