/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour(
    "focus_on_input_search",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [
        {
            content: "Check that the search input is focused.",
            trigger: ".o_snippet_search_filter_input",
            run: function () {
                if (this.anchor !== this.anchor.ownerDocument.activeElement) {
                    console.error("The search input is not focused");
                }
            },
        },
        {
            content: "Write something in the search box.",
            trigger: ".o_snippet_search_filter_input",
            run: "edit hello",
        },
        {
            content: "Write something in the search box.",
            trigger: ".o_snippet_search_filter_input:value(hello)",
        },
        ...wTourUtils.goToTheme(),
        {
            content: "Wait for loading",
            trigger: ".o_we_customize_theme_btn.active",
        },
        wTourUtils.goBackToBlocks(),
        {
            content: "Check that the search input is cleared and focused.",
            trigger: ".o_snippet_search_filter_input",
            run: async function () {
                // Ensure this check happens after any ongoing animation.
                await new Promise(resolve => requestAnimationFrame(resolve));

                if (this.anchor.value !== "") {
                    console.error("The search input is not cleared");
                }
                if (this.anchor !== this.anchor.ownerDocument.activeElement) {
                    console.error("The search input is not focused");
                }
            },
        },
    ]
);
