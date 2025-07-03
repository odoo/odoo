import { registry } from "@web/core/registry";
import { clickOnElement } from '@website/js/tours/tour_utils';
import { assertCartContains } from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('website_sale_reorder_from_portal', {
        url: '/my/orders',
        steps: () => [
        // Initial reorder, nothing in cart
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
            run: "click",
            expectUnloadPage: true,
        },
        clickOnElement('Reorder Again', '.o_wsale_reorder_button'),
<<<<<<< 3d4588798b4b52073d3b3e13c641ee70eb783709
        {
            content: "Confirm",
            trigger: ".o_wsale_reorder_confirm",
            run: "click",
            expectUnloadPage: true,
        },
        ...assertCartContains({productName: 'Reorder Product 1'}),
        ...assertCartContains({productName: 'Reorder Product 2'}),
||||||| 60ec0ba98a3f73d4720ca68c77ed4c69623ee08e
        clickOnElement('Confirm', '.o_wsale_reorder_confirm'),
        assertCartContains({productName: 'Reorder Product 1'}),
        assertCartContains({productName: 'Reorder Product 2'}),
=======
        {
            content: "Confirm",
            trigger: ".o_wsale_reorder_confirm",
            run: "click",
            expectUnloadPage: true,
        },
        assertCartContains({productName: 'Reorder Product 1'}),
        assertCartContains({productName: 'Reorder Product 2'}),
>>>>>>> cbc9bdd12612311e69015b6fb3bbd59e5adba20b
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
            },
            expectUnloadPage: true,
        },
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
            run: "click",
            expectUnloadPage: true,
        },
        clickOnElement('Reorder Again', '.o_wsale_reorder_button'),
<<<<<<< 3d4588798b4b52073d3b3e13c641ee70eb783709
        {
            content: "Confirm",
            trigger: ".modal .o_wsale_reorder_confirm",
            run: "click",
        },
        {
            content: "No",
            trigger: ".modal button:contains(No)",
            run: "click",
            expectUnloadPage: true,
        },
        ...assertCartContains({productName: 'Reorder Product 1'}),
        ...assertCartContains({productName: 'Reorder Product 2'}),
||||||| 60ec0ba98a3f73d4720ca68c77ed4c69623ee08e
        clickOnElement('Confirm', '.o_wsale_reorder_confirm'),
        clickOnElement('No', 'button:contains(No)'),
        assertCartContains({productName: 'Reorder Product 1'}),
        assertCartContains({productName: 'Reorder Product 2'}),
=======
        {
            content: "Confirm",
            trigger: ".modal .o_wsale_reorder_confirm",
            run: "click",
        },
        {
            content: "No",
            trigger: ".modal button:contains(No)",
            run: "click",
            expectUnloadPage: true,
        },
        assertCartContains({productName: 'Reorder Product 1'}),
        assertCartContains({productName: 'Reorder Product 2'}),
>>>>>>> cbc9bdd12612311e69015b6fb3bbd59e5adba20b
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
            },
            expectUnloadPage: true,
        },
        {
            content: 'Select first order',
            trigger: '.o_portal_my_doc_table a:first',
            run: "click",
            expectUnloadPage: true,
        },
        clickOnElement('Reorder Again', '.o_wsale_reorder_button'),
<<<<<<< 3d4588798b4b52073d3b3e13c641ee70eb783709
        {
            content: "Confirm",
            trigger: ".o_wsale_reorder_confirm",
            run: "click",
        },
        {
            content: "Yes",
            trigger: ".modal button:contains(Yes)",
            run: "click",
            expectUnloadPage: true,
        },
        ...assertCartContains({productName: 'Reorder Product 1'}),
        ...assertCartContains({productName: 'Reorder Product 2'}),
||||||| 60ec0ba98a3f73d4720ca68c77ed4c69623ee08e
        clickOnElement('Confirm', '.o_wsale_reorder_confirm'),
        clickOnElement('Yes', 'button:contains(Yes)'),
        assertCartContains({productName: 'Reorder Product 1'}),
        assertCartContains({productName: 'Reorder Product 2'}),
=======
        {
            content: "Confirm",
            trigger: ".o_wsale_reorder_confirm",
            run: "click",
        },
        {
            content: "Yes",
            trigger: ".modal button:contains(Yes)",
            run: "click",
            expectUnloadPage: true,
        },
        assertCartContains({productName: 'Reorder Product 1'}),
        assertCartContains({productName: 'Reorder Product 2'}),
>>>>>>> cbc9bdd12612311e69015b6fb3bbd59e5adba20b
        {
            content: "Check that quantity is 1",
            trigger: ".js_quantity[value='1']",
        },
        // Fourth reorder making sure confirmation dialog doesn't pop up unnecessary
        {
            content: "Deleting All products from cart",
            trigger: "div.js_cart_lines",
        },
        {
            trigger: "#cart_products:has(.o_cart_product:eq(3)):not(:has(.o_cart_product:eq(4)))",
        },
        {
            trigger: `a.js_delete_product:first`,
            run: "click",
        },
        {
            trigger: "#cart_products:has(.o_cart_product:eq(2)):not(:has(.o_cart_product:eq(3)))",
        },
        {
            trigger: `a.js_delete_product:first`,
            run: "click",
        },
        {
            trigger: "#cart_products:has(.o_cart_product:eq(1)):not(:has(.o_cart_product:eq(2)))",
        },
        {
            trigger: `a.js_delete_product:first`,
            run: "click",
        },
        {
            trigger: "#cart_products:has(.o_cart_product:eq(0)):not(:has(.o_cart_product:eq(1)))",
        },
        {
            trigger: `a.js_delete_product:first`,
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Go to my orders",
            trigger: 'body',
            run: () => {
                window.location = '/my/orders';
            },
            expectUnloadPage: true,
        },
        {
            content: "Select first order",
            trigger: '.o_portal_my_doc_table a:first',
            run: "click",
            expectUnloadPage: true,
        },
        clickOnElement('Reorder Again', '.o_wsale_reorder_button'),
<<<<<<< 3d4588798b4b52073d3b3e13c641ee70eb783709
        {
            content: "Confirm",
            trigger: ".o_wsale_reorder_confirm",
            run: "click",
            expectUnloadPage: true,
        },
        ...assertCartContains({productName: 'Reorder Product 1'}),
||||||| 60ec0ba98a3f73d4720ca68c77ed4c69623ee08e
        clickOnElement('Confirm', '.o_wsale_reorder_confirm'),
        assertCartContains({productName: 'Reorder Product 1'}),
=======
        {
            content: "Confirm",
            trigger: ".o_wsale_reorder_confirm",
            run: "click",
            expectUnloadPage: true,
        },
        assertCartContains({productName: 'Reorder Product 1'}),
>>>>>>> cbc9bdd12612311e69015b6fb3bbd59e5adba20b
        {
            content: "Check that quantity is 1",
            trigger: ".js_quantity[value='1']",
        },
    ]
});
