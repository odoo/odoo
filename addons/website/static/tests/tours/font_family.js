import { registerWebsitePreviewTour, goToTheme } from "@website/js/tours/tour_utils";
import { patch } from "@web/core/utils/patch";

registerWebsitePreviewTour(
    "website_font_family",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...goToTheme(),
        {
            content: "Click on the heading font family selector",
            trigger:
                "[data-container-title='Headings'] [data-label='Font Family'] .dropdown-toggle",
            run: "click",
        },
        {
            content: "Click on the 'Arvo' font we-button from the font selection list.",
            trigger: `.o_popover [data-action-value="'Arvo'"]`,
            run: "click",
        },
        {
            content: "Verify that the 'Arvo' font family is correctly applied to the heading.",
            trigger: "button.dropdown-toggle span[style*='font-family: Arvo;']",
        },
        {
            content: "Open the heading font family selector",
            trigger: "button:has(span[style*='font-family: Arvo;'])",
            run: "click",
        },
        {
            trigger:
                "[data-container-title='Headings'] [data-label='Font Family'] .dropdown-toggle",
            // This is a workaround to prevent the _reloadBundles method from being called.
            // It addresses the issue where selecting a we-button with data-no-bundle-reload,
            // such as o_we_add_font_btn.
            run: function () {
                const options = odoo.loader.modules.get(
                    "@website/builder/plugins/customize_website_plugin"
                )["CustomizeWebsitePlugin"];
                patch(options.prototype, {
                    async reloadBundles() {
                        console.error("The font family selector value get reload to its default.");
                    },
                });
            },
        },
        {
            content: "Click on the 'Add a custom font' button",
            trigger: ".o_popover .o_we_add_font_btn",
            run: "click",
        },
        {
            content: "Wait for the modal to open and then refresh",
            trigger: "body .o_dialog button.btn-secondary",
            run: "click",
        },
        {
            content: "Check that 'Arvo' font family is still applied and not reverted",
            trigger: "button:has(span[style*='font-family: Arvo;'])",
        },
    ]
);
