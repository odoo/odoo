/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import tourUtils from "@sign/js/tours/tour_utils";

registry.category("web_tour.tours").add("sign_template_creation_tour", {
    url: "/odoo?debug=1",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Sign App",
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
            content: 'Search template "blank_template"',
            trigger: ".o_cp_searchview input",
            run: "fill blank_template",
        },
        {
            content: "Search Document Name",
            trigger: ".o_searchview_autocomplete .o_menu_item:first",
            run: "click",
        },
        {
            content: "Enter Template Edit Mode",
            trigger: '.o_kanban_record span:contains("blank_template")',
            run: "click",
        },
        {
            content: "Wait for iframe to load PDF",
            trigger: ":iframe #viewerContainer",
        },
        {
            content: "Wait for page to be loaded",
            trigger: ":iframe .page[data-page-number='1'] .textLayer",
            timeout: 30000, //In view mode, pdf loading can take a long time
        },
        {
            content: "Drop Signature Item",
            trigger: ":iframe .o_sign_field_type_button:contains(Signature)",
            run() {
                tourUtils.dragAndDropSignItemAtHeight(this.anchor, 0.5, 0.25);
            },
        },
        {
            content: "Drop Name Sign Item",
            trigger: ":iframe .o_sign_field_type_button:contains(Name)",
            run() {
                tourUtils.dragAndDropSignItemAtHeight(this.anchor, 0.25, 0.25);
            },
        },
        {
            content: "Drop Text Sign Item",
            trigger: ":iframe .o_sign_field_type_button:contains(Text)",
            run() {
                tourUtils.dragAndDropSignItemAtHeight(this.anchor, 0.15, 0.25);
            },
        },
        {
            content: "Open popover on name sign item",
            trigger: ':iframe .o_sign_sign_item:contains("Name") .o_sign_item_display',
            run: "click",
        },
        {
            content: "Change responsible",
            trigger: ".o_popover .o_input_dropdown input",
            run: "edit employee",
        },
        {
            content: "select employee",
            trigger: '.o_popover .o_input_dropdown .dropdown .dropdown-item:contains("Employee")',
            run: "click",
        },
        {
            content: "Validate changes",
            trigger: ".o_popover .o_sign_validate_field_button",
            run: "click",
        },
        {
            content: "Drop Selection Sign Item",
            trigger: ":iframe .o_sign_field_type_button:contains(Selection)",
            run() {
                tourUtils.dragAndDropSignItemAtHeight(this.anchor, 0.75, 0.25);
            },
        },
        {
            content: "Open popover on Selection sign item",
            trigger: ':iframe .o_sign_sign_item:contains("Selection") .o_sign_item_display',
            run: "click",
        },
        {
            content: "Write new selection option name",
            trigger: ".o_popover .o_input_dropdown input",
            run: "edit option",
        },
        {
            content: "Create new selection option",
            trigger: '.o_popover .o_input_dropdown .dropdown a:contains("Create")',
            run: "click",
        },
        {
            content: "Check option is added",
            trigger: '.o_popover #o_sign_select_options_input .o_tag_badge_text:contains("option")',
            run: "click",
        },
        {
            content: "Validate changes",
            trigger: ".o_popover .o_sign_validate_field_button",
            run: "click",
        },
        {
            content: "Open popover on text sign item",
            trigger: ":iframe .o_sign_sign_item:contains('Text') .o_sign_item_display",
            run: "click",
        },
        {
            content: "Change text placeholder",
            trigger: ".o_popover .o_popover_placeholder input",
            run: "edit placeholder && click .o_popover",
        },
        {
            content: "Validate changes",
            trigger: ".o_popover .o_sign_validate_field_button",
            run: "click",
        },
        {
            content: "Change template name",
            trigger: ".o_sign_template_name_input",
            run: "edit filled_template && click body",
        },
        {
            trigger: ".breadcrumb .o_back_button",
            run: "click",
        },
    ],
});
