/** @odoo-module **/

import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";

// This tour relies on data created on the Python test.
registry.category("web_tour.tours").add('sale_signature', {
    url: '/my/quotes',
    steps: () => [
    {
        content: "open the test SO",
        trigger: 'a:contains(/^test SO$/)',
        run: "click",
    },
    {
        content: "click sign",
        trigger: 'a:contains("Sign")',
        run: "click",
    },
    {
        content: "check submit is enabled",
        trigger: '.o_portal_sign_submit:enabled',
    },
    {
        trigger: ".modal .o_web_sign_name_and_signature input:value(Joel Willis)"
    },
    {
        content: "click select style",
        trigger: '.modal .o_web_sign_auto_select_style button',
        run: "click",
    },
    {
        content: "click style 4",
        trigger: ".o-dropdown-item:eq(3)",
        run: "click",
    },
    {
        content: "click submit",
        trigger: '.modal .o_portal_sign_submit:enabled',
        run: "click",
    },
    {
        content: "check it's confirmed",
        trigger: '#quote_content:contains("Thank You")',
        run: "click",
    }, {
        trigger: '#quote_content',
        run: function () {
            redirect("/odoo");
        },  // Avoid race condition at the end of the tour by returning to the home page.
    },
    {
        trigger: 'nav',
    }
]});

registry.category("web_tour.tours").add("sale_signature_without_name", {
    steps: () => [
        {
            content: "Sign & Pay",
<<<<<<< 4fe90167266a92c3a5941eac9a6a2084a80056ac
            trigger:
                ".o_portal_sale_sidebar .btn-primary, :iframe .o_portal_sale_sidebar .btn-primary",
||||||| c2187d78cf01cc3480ad82600df6ca36d3700d04
            trigger: ":iframe .o_portal_sale_sidebar .btn-primary",
=======
            trigger: ":iframe .o_portal_sale_sidebar .btn-primary",
            alt_trigger: ".o_portal_sale_sidebar .btn-primary",
>>>>>>> 7075eddb6a9334fa7e83aa5830be6fc69de0564f
            run: "click",
        },
        {
            content: "click submit",
<<<<<<< 4fe90167266a92c3a5941eac9a6a2084a80056ac
            trigger: ".o_portal_sign_submit:enabled, :iframe .o_portal_sign_submit:enabled",
||||||| c2187d78cf01cc3480ad82600df6ca36d3700d04
            trigger: ":iframe .o_portal_sign_submit:enabled",
=======
            trigger: ":iframe .o_portal_sign_submit:enabled",
            alt_trigger: ".o_portal_sign_submit:enabled",
>>>>>>> 7075eddb6a9334fa7e83aa5830be6fc69de0564f
            run: "click",
        },
        {
            content: "check error because no name",
<<<<<<< 4fe90167266a92c3a5941eac9a6a2084a80056ac
            trigger:
                '.o_portal_sign_error_msg:contains("Signature is missing."), :iframe .o_portal_sign_error_msg:contains("Signature is missing.")',
||||||| c2187d78cf01cc3480ad82600df6ca36d3700d04
            trigger: ':iframe .o_portal_sign_error_msg:contains("Signature is missing.")',
=======
            trigger: ':iframe .o_portal_sign_error_msg:contains("Signature is missing.")',
            alt_trigger: '.o_portal_sign_error_msg:contains("Signature is missing.")'
>>>>>>> 7075eddb6a9334fa7e83aa5830be6fc69de0564f
        },
    ],
});
