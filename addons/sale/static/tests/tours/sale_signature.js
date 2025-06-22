/** @odoo-module **/

import { registry } from "@web/core/registry";

// This tour relies on data created on the Python test.
registry.category("web_tour.tours").add('sale_signature', {
    test: true,
    url: '/my/quotes',
    steps: () => [
    {
        content: "open the test SO",
        trigger: 'a:containsExact("test SO")',
    },
    {
        content: "click sign",
        trigger: 'a:contains("Sign")',
    },
    {
        content: "check submit is enabled",
        trigger: '.o_portal_sign_submit:enabled',
        run: function () {},
    },
    {
        content: "click select style",
        trigger: '.o_web_sign_auto_select_style button',
    },
    {
        content: "click style 4",
        trigger: '.o_web_sign_auto_select_style .dropdown-item:eq(3)',
    },
    {
        content: "click submit",
        trigger: '.o_portal_sign_submit:enabled',
    },
    {
        content: "check it's confirmed",
        trigger: '#quote_content:contains("Thank You")',
    }, {
        trigger: '#quote_content',
        run: function () {
            window.location.href = window.location.origin + '/web';
        },  // Avoid race condition at the end of the tour by returning to the home page.
    },
    {
        trigger: 'nav',
        run: function() {},
    }
]});

registry.category("web_tour.tours").add("sale_signature_without_name", {
    steps: () => [
        {
            content: "Sign & Pay",
            trigger: ".o_portal_sale_sidebar .btn-primary",
            alt_trigger: "iframe .o_portal_sale_sidebar .btn-primary",
            run: "click",
        },
        {
            content: "click submit",
            trigger: ".o_portal_sign_submit:enabled",
            alt_trigger: "iframe .o_portal_sign_submit:enabled",
            run: "click",
        },
        {
            content: "check error because no name",
            trigger: '.o_portal_sign_error_msg:contains("Signature is missing.")',
            alt_trigger: 'iframe .o_portal_sign_error_msg:contains("Signature is missing.")',
            run: () => {},
        },
    ],
});
