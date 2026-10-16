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
            trigger: "we-select[data-variable='headings-font']",
            run: "click",
        },
        {
            content: "Click on the 'Arvo' font we-button from the font selection list.",
            trigger: "we-selection-items we-button[data-font-family='Arvo']",
            run: "click",
        },
        {
            content: "Verify that the 'Arvo' font family is correctly applied to the heading.",
            trigger: "we-toggler[style*='font-family: Arvo;']",
        },
        {
            content: "Open the heading font family selector",
            trigger: "we-toggler[style*='font-family: Arvo;']",
            run: "click",
        },
        {
            trigger: "we-select[data-variable='headings-font']",
            // This is a workaround to prevent the _reloadBundles method from being called.
            // It addresses the issue where selecting a we-button with data-no-bundle-reload,
            // such as o_we_add_font_btn.
            run: function () {
                const options = odoo.loader.modules.get("@web_editor/js/editor/snippets.options")[
                    Symbol.for("default")
                ];
                patch(options.Class.prototype, {
                    async _refreshBundles() {
                        console.error("The font family selector value get reload to its default.");
                    },
                });
            },
        },
        {
            content: "Click on the 'Add a custom font' button",
            trigger: "we-select[data-variable='headings-font'] .o_we_add_font_btn",
            run: "click",
        },
        {
            content: "Wait for the modal to open and then refresh",
            trigger: "body .o_dialog button.btn-secondary",
            run: "click",
        },
        {
            content: "Check that 'Arvo' font family is still applied and not reverted",
            trigger: "we-toggler[style*='font-family: Arvo;']",
        },
    ]
);

registerWebsitePreviewTour(
    "website_delete_uploaded_font",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...goToTheme(),
        {
            content: "Open the font family selector",
            trigger: "we-select[data-variable='font'] we-toggler",
            run: "click",
        },
        {
            content: "Check that only the uploaded font can be deleted",
            trigger: "we-select[data-variable='font'] we-selection-items",
            run() {
                const deleteBtnCount = this.anchor.querySelectorAll(".o_we_delete_font_btn").length;
                if (deleteBtnCount !== 1) {
                    throw new Error(`Expected 1 font to be deletable, found ${deleteBtnCount}`);
                }
            },
        },
        {
            content: "Click on the delete button of the uploaded font",
            trigger: `we-button[data-font-family='demo,font'] .o_we_delete_font_btn`,
            run: "click",
        },
        {
            content: "Confirm the font deletion",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            content: "Check that the font was deleted without any error",
            trigger: ":iframe body:not(:has(.o_notification_bar.bg-danger))",
        },
    ]
);
