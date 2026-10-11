import { registerWebsitePreviewTour, goToTheme } from "@website/js/tours/tour_utils";
import { patch } from "@web/core/utils/patch";

registerWebsitePreviewTour(
    "website_font_family",
    {
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
        {
            content: "Click on the 'Add a custom font' button",
            trigger: ".o_popover .o_we_add_font_btn",
            run: "click",
        },
        {
            content: "Fetch Google fonts",
            trigger: ".modal #google_font",
            run: "click",
        },
        {
            content: "Select a Google font previewed in its own font",
            trigger: `.modal .dropdown-item:has(> span[style*='font-family: "Second test font"'][style*='font-size: 1rem'])`,
            run: "click",
        },
        {
            content: "Check that the preview input is displayed",
            trigger: ".modal #font_preview_text[placeholder='Type here to preview text']",
        },
        {
            content: "Check that the 3 previews are correctly set in the modal",
            trigger:
                ".modal .o_website_font_preview_sample div[style*='Second test font']:count(3)",
        },
        {
            content: "Edit the text of all font previews",
            trigger: ".modal #font_preview_text",
            run: "edit Sample text",
        },
        {
            content: "Check that all font previews use the edited text",
            trigger: ".modal .o_website_font_preview_sample span:contains('Sample text'):count(3)",
        },
        {
            content: "Change the font preview size",
            trigger: ".modal #font_preview_size",
            run: "select 32",
        },
        {
            content: "Check that all font previews use the selected size",
            trigger:
                ".modal .o_website_font_preview_sample span[style*='font-size: 32px']:count(3)",
        },
        {
            content: "Close the font dialog",
            trigger: ".modal button.btn-secondary:contains('Discard')",
            run: "click",
        },
        {
            content: "Check that the font dialog is closed",
            trigger: "body:not(:has(.o_website_add_font_dialog))",
        },
    ]
);
