/** @odoo-module **/

import { registry } from "@web/core/registry";
import { assertCartContains } from '@website_sale/js/tours/tour_utils';
import { clickOnElement } from '@website/js/tours/tour_utils';

registry.category("web_tour.tours").add('website_sale_reorder_from_portal', {
        url: '/my/orders',
        steps: () => [
        // Initial reorder, nothing in cart
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
            run: "click",
        },
        clickOnElement('Reorder Again', '.o_wsale_reorder_button'),
        clickOnElement('Confirm', '.o_wsale_reorder_confirm'),
        assertCartContains({productName: 'Reorder Product 1'}),
        assertCartContains({productName: 'Reorder Product 2'}),
        {
            content: "Check that quantity is 1",
            trigger: ".js_quantity[value='1']",
            run: "edit Test",
        },
        // Second reorder, add reorder to cart
        {
            content: "Go back to my orders",
            trigger: "body",
            run() {
                window.location = "/my/orders";
            }
        },
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
            run: "click",
        },
        clickOnElement('Reorder Again', '.o_wsale_reorder_button'),
        clickOnElement('Confirm', '.o_wsale_reorder_confirm'),
        clickOnElement('No', 'button:contains(No)'),
        assertCartContains({productName: 'Reorder Product 1'}),
        assertCartContains({productName: 'Reorder Product 2'}),
        {
            content: "Check that quantity is 2",
            trigger: ".js_quantity[value='2']",
            run: "edit Test",
        },
        // Third reorder, clear cart and reorder
        {
            content: "Go back to my orders",
            trigger: "body",
            run() {
                window.location = "/my/orders";
            }
        },
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
            run: "click",
        },
        clickOnElement('Reorder Again', '.o_wsale_reorder_button'),
        clickOnElement('Confirm', '.o_wsale_reorder_confirm'),
        clickOnElement('Yes', 'button:contains(Yes)'),
        assertCartContains({productName: 'Reorder Product 1'}),
        assertCartContains({productName: 'Reorder Product 2'}),
        {
            content: "Check that quantity is 1",
            trigger: ".js_quantity[value='1']",
        },
    ]
});
