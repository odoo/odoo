/** @odoo-module **/

import { registry } from "@web/core/registry";
import wsTourUtils from '@website_sale/js/tours/tour_utils';
import wTourUtils from '@website/js/tours/tour_utils';

registry.category("web_tour.tours").add('website_sale_reorder_from_portal', {
        test: true,
        url: '/my/orders',
        steps: () => [
        // Initial reorder, nothing in cart
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
        },
        wTourUtils.clickOnElement('Reorder Again', '.o_wsale_reorder_button'),
        wTourUtils.clickOnElement('Confirm', '.o_wsale_reorder_confirm'),
        wsTourUtils.assertCartContains({productName: 'Reorder Product 1'}),
        wsTourUtils.assertCartContains({productName: 'Reorder Product 2'}),
        {
            content: "Check that quantity is 1",
            trigger: ".js_quantity[value='1']",
        },
        // Second reorder, add reorder to cart
        {
            content: "Go back to my orders",
            trigger: "body",
            run: () => {
                window.location = "/my/orders";
            }
        },
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
        },
        wTourUtils.clickOnElement('Reorder Again', '.o_wsale_reorder_button'),
        wTourUtils.clickOnElement('Confirm', '.o_wsale_reorder_confirm'),
        wTourUtils.clickOnElement('No', 'button:contains(No)'),
        wsTourUtils.assertCartContains({productName: 'Reorder Product 1'}),
        wsTourUtils.assertCartContains({productName: 'Reorder Product 2'}),
        {
            content: "Check that quantity is 2",
            trigger: ".js_quantity[value='2']",
        },
        // Third reorder, clear cart and reorder
        {
            content: "Go back to my orders",
            trigger: "body",
            run: () => {
                window.location = "/my/orders";
            }
        },
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
        },
        wTourUtils.clickOnElement('Reorder Again', '.o_wsale_reorder_button'),
        wTourUtils.clickOnElement('Confirm', '.o_wsale_reorder_confirm'),
        wTourUtils.clickOnElement('Yes', 'button:contains(Yes)'),
        wsTourUtils.assertCartContains({productName: 'Reorder Product 1'}),
        wsTourUtils.assertCartContains({productName: 'Reorder Product 2'}),
        {
            content: "Check that quantity is 1",
            trigger: ".js_quantity[value='1']",
            isCheck: true,
        },
    ]
});
