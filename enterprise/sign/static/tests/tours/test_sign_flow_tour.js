/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("test_sign_flow_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
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
            content: 'Search template "template_1_roles"',
            trigger: ".o_cp_searchview input",
            tooltipPosition: "bottom",
            run: "edit template_1_role(2)",
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
            trigger: '.o_list_button button:contains("Sign Now")',
        },
        {
            content: "Click Sign Now",
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
            trigger: ':iframe .o_sign_sign_item_navigator:contains("Click to start")',
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            content: "Fill the sign item",
            trigger: ":iframe input.o_sign_sign_item",
            run: "edit Mitchell Admin",
        },
        {
            content: "Click next 1",
            trigger: ':iframe .o_sign_sign_item_navigator:contains("next")',
            run: "click",
        },
        {
            content: "Click it",
            trigger: ":iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            trigger: ":iframe :not(:has(.o_sign_sign_item_navigator))",
        },
        {
            isActive: ["auto"],
            trigger: ":iframe button.o_sign_sign_item:has(img)",
            run: "click",
        },
        {
            content: "Click on auto button",
            trigger: ".o_web_sign_auto_button",
            run: "click",
        },
        {
            trigger: "canvas.o_web_sign_signature",
        },
        {
            content: "Sign",
            trigger: 'button.btn-primary:contains("Sign all")',
            run: "click",
        },
        {
            trigger: ".o_sign_validate_banner",
        },
        {
            content: "Validate & Send Completed Document",
            trigger: "button:contains('Validate & Send Completed Document')",
            run: "click",
        },
        {
            trigger:
                ".modal-dialog .modal-body:contains(You will get the signed document by email.)",
        },
        {
            content: "Close modal",
            trigger: ".modal-footer button.btn-secondary:contains(close)",
            run: "click",
        },
    ],
});
