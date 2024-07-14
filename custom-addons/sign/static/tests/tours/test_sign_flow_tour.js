/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("test_sign_flow_tour", {
    test: true,
    url: "/web",
    steps: () => [
        stepUtils.showAppsMenuItem(),
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
            content: 'Search template "template_1_roles"',
            trigger: ".o_cp_searchview input",
            run: "text template_1_role(2)",
            position: "bottom",
        },
        {
            content: "Search Document Name",
            trigger: ".o_searchview_autocomplete .o_menu_item:first",
            run: "click",
        },
        {
            content: "list view",
            trigger: "button.o_list",
            run: "click",
        },
        {
            content: "Click Sign Now",
            extra_trigger: '.o_list_button button:contains("Sign Now")',
            trigger: "button:contains('Sign Now')",
            run: "click",
        },
        {
            content: "Click sign",
            trigger: "button[name='sign_directly']",
            run: "click",
        },
        {
            content: "Click to start",
            trigger: 'iframe .o_sign_sign_item_navigator:contains("Click to start")',
            position: "bottom",
        },
        {
            trigger: "iframe input.o_sign_sign_item:focus",
            auto: true,
            run() {},
        },
        {
            content: "Fill the sign item",
            trigger: "iframe input.o_sign_sign_item",
            run: "text Mitchell Admin",
        },
        {
            content: "Click next 1",
            trigger: 'iframe .o_sign_sign_item_navigator:contains("next")',
            run: "click",
        },
        {
            content: "Click sign it",
            trigger: 'iframe .o_sign_sign_item_navigator:contains("sign it")',
            run: "click",
        },
        {
            trigger: "iframe button.o_sign_sign_item:has(> img)",
            extra_trigger: "iframe :not(:has(.o_sign_sign_item_navigator))",
            auto: true,
        },
        {
            content: "Click on auto button",
            trigger: ".o_web_sign_auto_button",
            run: "click",
        },
        {
            content: "Sign",
            trigger: 'button.btn-primary:contains("Sign all")',
            extra_trigger: "canvas.jSignature",
            run() {
                setTimeout(() => {
                    this.$anchor.click();
                }, 1000);
            },
        },
        {
            content: "Validate & Send Completed Document",
            extra_trigger: ".o_sign_validate_banner",
            trigger: "button:contains('Validate & Send Completed Document')",
            run: "click",
        },
        {
            content: "view",
            extra_trigger: ".modal-dialog",
            trigger: ".modal-footer button.btn-primary",
            alt_trigger: ".modal-footer button.btn-secondary",
            run: "click",
        },
    ],
});
