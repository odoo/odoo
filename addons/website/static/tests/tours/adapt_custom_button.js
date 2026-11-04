/** @odoo-module */

import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "adapt_custom_button_on_drop",
    {
        url: "/",
        edition: true,
    },
    () => [
        {
            content: "Check that the custom button snippet is present",
            trigger: "#snippet_custom_body .oe_snippet[name='Custom Button']",
            run: () => null,
        },
        {
            content: "Drag the Custom Button and drop it near the header Contact us button",
            trigger:
                "#oe_snippets .oe_snippet[name='Custom Button'] .oe_snippet_thumbnail:not(.o_we_already_dragging)",
            run: "drag_and_drop :iframe header [data-snippet='s_text_block']",
        },
        {
            content: "Check that the custom button is NOT wrapped in <p>",
            trigger: ":iframe header .s_custom_snippet:not(.s_custom_button)",
            run() {
                const customButtonEl = this.anchor;
                if (customButtonEl.parentNode.tagName === "P") {
                    throw new Error(
                        "Custom button should not be wrapped in <p> when sibling button is present"
                    );
                }
            },
        },
    ]
);
