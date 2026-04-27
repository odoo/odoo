/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("shared_sign_request_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "Open Sign APP",
            trigger: '.o_app[data-menu-xmlid="sign.menu_document"]',
            run: "click",
        },
        {
            content: "Click on Template Menu",
            trigger: 'a[data-menu-xmlid="sign.sign_template_menu"]',
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_last_breadcrumb_item > span:contains('Templates')",
        },
        {
            content: "Remove My Favorites filter",
            trigger: ".o_cp_searchview .o_facet_remove",
            run: "click",
        },
        {
            content: 'Search template "template_1_role"',
            trigger: ".o_cp_searchview input",
            run: "edit template_1_role",
        },
        {
            content: "Search Document Name",
            trigger: ".o_searchview_autocomplete .o_menu_item:first",
            run: "click",
        },
        {
            trigger: '.o_kanban_record span:contains("template_1_role")',
        },
        {
            content: "Share the template",
            trigger: '.o_kanban_record:first button:contains("Share"):first',
            run: "click",
        },
        {
            content: "Go on signing page",
            trigger: ".o_field_CopyClipboardChar",
            run: function () {
                const share_link = this.anchor.childNodes[0].firstChild.textContent;
                // Retrieve the link without the origin to avoid
                // mismatch between localhost:8069 and 127.0.0.1:8069
                // when running the tour with chrome headless
                const regex = "/sign/document/mail/.*";
                const url = share_link.match(regex)[0];
                window.location.href = window.location.origin + url;
            },
            expectUnloadPage: true,
        },
        {
            content: "Fill the sign item",
            trigger: ":iframe input.o_sign_sign_item",
            run: "edit Mitchell Admin",
        },
        {
            content: "Validate & Send Completed Document",
            trigger: ".o_validate_button",
            run: "click",
        },
        {
            trigger: '.modal-title:contains("Final Validation")',
        },
        {
            content: "Fill name",
            trigger: "#o_sign_public_signer_name_input",
            run: "edit Mitchell Admin",
        },
        {
            content: "Fill email",
            trigger: "#o_sign_public_signer_mail_input",
            run: "edit mitchell.admin@public.com",
        },
        {
            content: "Validate & Send",
            trigger: '.modal-footer button:contains("Validate & Send")',
            run: "click",
        },
        {
            trigger: `.modal-title:contains("It's signed!")`,
        },
    ],
});

registry.category("web_tour.tours").add("sign_resend_expired_link_tour", {
    steps: () => [
        {
            trigger: "a:contains(Send a new link)",
        },
        {
            trigger: ".btn.btn-primary",
            content: "Click to resend the url",
            run: "click",
            expectUnloadPage: true,
        },
    ],
});
