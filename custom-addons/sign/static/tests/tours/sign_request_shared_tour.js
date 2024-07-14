/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("shared_sign_request_tour", {
    test: true,
    url: "/web",
    steps: () => [
        {
            content: "Open Sign APP",
            trigger: '.o_app[data-menu-xmlid="sign.menu_document"]',
            run: "click",
        },
        {
            content: "Remove My Favorites filter",
            trigger: ".o_cp_searchview .o_facet_remove",
            run: "click",
        },
        {
            content: 'Search template "template_1_role"',
            trigger: ".o_cp_searchview input",
            run: "text template_1_role",
        },
        {
            content: "Search Document Name",
            trigger: ".o_searchview_autocomplete .o_menu_item:first",
            run: "click",
        },
        {
            content: "Share the template",
            trigger: '.o_kanban_record_bottom:first button:contains("Share"):first',
            extra_trigger: '.oe_kanban_main:first span:contains("template_1_role")',
            run: "click",
        },
        {
            content: "Go on signing page",
            trigger: ".o_field_CopyClipboardChar",
            run: function () {
                const share_link = this.$anchor.contents()[0].firstChild.textContent;
                // Retrieve the link without the origin to avoid
                // mismatch between localhost:8069 and 127.0.0.1:8069
                // when running the tour with chrome headless
                const regex = "/sign/document/mail/.*";
                const url = share_link.match(regex)[0];
                window.location.href = window.location.origin + url;
            },
        },
        {
            content: "Fill the sign item",
            trigger: "iframe input.o_sign_sign_item",
            run: "text Mitchell Admin",
        },
        {
            content: "Validate & Send Completed Document",
            trigger: ".o_validate_button",
            run: "click",
        },
        {
            content: "Fill name",
            trigger: "#o_sign_public_signer_name_input",
            extra_trigger: '.modal-title:contains("Final Validation")',
            run: "text Mitchell Admin",
        },
        {
            content: "Fill email",
            trigger: "#o_sign_public_signer_mail_input",
            run: "text mitchell.admin@public.com",
        },
        {
            content: "Validate & Send",
            trigger: '.modal-footer button:contains("Validate & Send")',
            run: "click",
        },
        {
            content: "Download Document",
            trigger: "button.btn.btn-primary",
            extra_trigger: '.modal-title:contains("Thank you!")',
            run() {},
        },
    ],
});
