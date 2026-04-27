/** @odoo-module */

import { registry } from "@web/core/registry";
import { assertEqual } from "@web_studio/../tests/tours/tour_helpers";

registry.category("web_tour.tours").add("website_studio_listing_and_page", {
    url: "/odoo/action-studio?debug=1&mode=home_menu",
    steps: () => [
        {
            trigger: "a.o_menuitem:contains('StudioApp')",
            run: "click",
        },
        {
            trigger: ".o_menu_sections a:contains('Model Pages')",
            run: "click",
        },
        {
            content: "Create a listing page",
            trigger: ".o-kanban-button-new",
            run: "click",
        },
        {
            content: "Set the name of the page",
            trigger: "div[name='name'] input",
            run: "edit MyCustom Name && press Tab",
        },
        {
            trigger: "div[name='name_slugified'] input:value(mycustom-name)",
        },
        {
            content: "listing is displayed in the menu by default",
            trigger: "div[name='use_menu'] input:checked",
        },
        {
            content:
                "creating a listing automatically creates a detailed page for each record to be consulted separately",
            trigger: "div[name='auto_single_page'] input:checked",
        },
        {
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_back_button",
            run: "click",
        },
        {
            trigger: ".o_kanban_view",
            run() {
                const pages = this.anchor.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)");
                assertEqual(pages.length, 1);
                assertEqual(pages[0].querySelector("[data-section='title']").textContent, "MyCustom Name");
            },
        },
    ],
});

registry.category("web_tour.tours").add("website_studio_listing_without_page", {
    url: "/odoo/action-studio?debug=1&mode=home_menu",
    steps: () => [
        {
            trigger: "a.o_menuitem:contains('StudioApp')",
            run: "click",
        },
        {
            trigger: ".o_menu_sections a:contains('Model Pages')",
            run: "click",
        },
        {
            content: "Create a listing page",
            trigger: ".o-kanban-button-new",
            run: "click",
        },
        {
            content: "Set the name of the page",
            trigger: "div[name='name'] input",
            run: "edit MyCustom Name && press Tab",
        },
        {
            trigger: "div[name='name_slugified'] input:value(mycustom-name)",
        },
        {
            content: "listing is displayed in the menu by default",
            trigger: "div[name='use_menu'] input:checked",
        },
        {
            content:
                "creating a listing automatically creates a detailed page for each record to be consulted separately",
            trigger: "div[name='auto_single_page'] input:checked",
        },
        {
            content: "Uncheck the toggle and only create the listing",
            trigger: "div[name='auto_single_page'] input",
            run: "click",
        },
        {
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_back_button",
            run: "click",
        },
        {
            trigger: ".o_kanban_view",
            run() {
                const pages = this.anchor.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)");
                assertEqual(pages.length, 1);
                assertEqual(pages[0].querySelector("[data-section='title']").textContent, "MyCustom Name");
            },
        },
    ],
});

registry.category("web_tour.tours").add("website_studio_website_form", {
    steps: () => [
        {
            trigger: ".o_edit_website_container .o-website-btn-custo-primary",
            run: "click",
        },
        {
            trigger: "#snippet_groups",
        },
        {
            trigger: ":iframe .odoo-editor-editable .s_website_form .o_default_snippet_text",
            run: "click",
        },
        {
            trigger: ".snippet-option-WebsiteFormEditor we-select:eq(0)",
            run: "click",
        },
        {
            trigger: ".snippet-option-WebsiteFormEditor we-select:eq(0).o_we_widget_opened"
        },
        {
            trigger: ".snippet-option-WebsiteFormEditor we-button[data-select-action='website_studio.form_more_model']",
            run: "click",
        },
        {
            trigger: ".modal .o_list_view"
        },
        {
            trigger: ".modal .o_searchview_input",
            run: "edit x_test_model && press Enter"
        },
        {
            trigger: ".modal .o_data_row:contains(x_test_model) .o_data_cell",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal)) .o_we_user_value_widget[data-name='enable_website_form_access'].active"
        },
        {
            trigger: ":iframe form[data-model_name='x_test_model']",
        },
        {
            trigger: ".o_we_website_top_actions button[data-action='save']",
            run: "click",
        },
        {
            trigger: ".o_website_preview:not(.editor_enable) :iframe form[data-model_name='x_test_model']",
        },
    ]
});
