import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "header_text_element_reset",
    {
        url: "/",
        edition: true,
    },
    () => [
        {
            content: "Edit the header text element",
            trigger: ":iframe #wrapwrap > header .s_text_block span.o_force_ltr small",
            run: "editor EDITED",
        },
        {
            content: "Check that the header text element is marked dirty",
            trigger: ":iframe #wrapwrap > header .o_dirty:contains(EDITED)",
        },
        {
            content: "Select the header to show its options",
            trigger: ":iframe #wrapwrap > header .s_text_block",
            run: "click",
        },
        {
            content: "Hide the header text element",
            trigger: "we-customizeblock-option.snippet-option-HeaderElements we-button[title='Show/hide text element']",
            run: "click",
        },
        {
            content: "Wait for the editor to reload without the header text element",
            trigger: ":iframe #wrapwrap > header:not(:has(.s_text_block span.o_force_ltr))",
        },
        {
            content: "Wait for the editor to be ready again",
            trigger: "#oe_snippets.o_loaded",
        },
    ]
);
