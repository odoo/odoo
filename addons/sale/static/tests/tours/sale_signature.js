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
        expectUnloadPage: true,
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
        trigger: ".modal canvas.o_web_sign_signature",
        run: "canvasNotEmpty",
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
        expectUnloadPage: true,
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
        expectUnloadPage: true,
    },
    {
        trigger: 'nav',
    }
]});

registry.category("web_tour.tours").add("sale_signature_without_name", {
    steps: () => [
        {
            content: "Sign & Pay",
            trigger:
                ".o_portal_sale_sidebar .btn-primary, :iframe .o_portal_sale_sidebar .btn-primary",
            run: "click",
        },
        {
            content: "click submit",
            trigger: ".o_portal_sign_submit:enabled, :iframe .o_portal_sign_submit:enabled",
            run: "click",
        },
        {
            content: "check error because no name",
            trigger:
                '.o_portal_sign_error_msg:contains("Signature is missing."), :iframe .o_portal_sign_error_msg:contains("Signature is missing.")',
        },
    ],
});
