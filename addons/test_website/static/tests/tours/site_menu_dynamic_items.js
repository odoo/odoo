import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_site_menu_dynamic_items",
    {
        url: "/",
    },
    () => [
        {
            content: "Ensure the preview is visible",
            trigger: ".o_website_preview .o_iframe_container iframe"
        },
        {
            content: "Open Site backend menu as early possible",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
            run: "click",
        },
        {
            content: "Menu is open",
            trigger: '.o_menu_sections [data-menu-xmlid="website.menu_site"].show',
        },
        {
            content: "Dynamic Page Properties item appears in open menu",
            trigger: '[data-menu-xmlid="website.menu_page_properties"]',
            timeout: 3000,
        },
        {
            content: "Menu editor remains visible with dynamic items",
            trigger: '[data-menu-xmlid="website.menu_edit_menu"]',
        },
    ]
);

