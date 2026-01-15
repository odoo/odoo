import { registry } from "@web/core/registry";
import { assertCartContains } from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('website_sale_reorder_from_portal', {
        url: '/my/orders',
        steps: () => [
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: 'Reorder Again',
            trigger: '.o_wsale_reorder_button',
            run: "click",
            expectUnloadPage: true,
        },
        ...assertCartContains({productName: 'Reorder Product 1'}),
        ...assertCartContains({productName: 'Reorder Product 2'}),
        {
            content: "Check that quantity is 1",
            trigger: ".js_quantity[value='1']",
            run: "edit Test",
        },
    ]
});
