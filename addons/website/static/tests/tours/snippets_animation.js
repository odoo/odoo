/** @odoo-module */

import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "footer_slideout_and_animation",
    {
        url: "/",
        edition: true,
    },
    () => [
        // Insert a big snippet to make the footer slideout below
        ...insertSnippet({ id: "s_faq_horizontal", name: "Topics List", groupName: "Text" }),
        {
            content: "Click on a footer column",
            trigger: ":iframe #footer .container > .row > div:contains('Useful Links')",
            run: "click",
        },
        {
            trigger:
                ".snippet-option-WebsiteAnimate [data-animation-mode=onAppearance]:not(:visible)",
            content: "Set Column Animation to On Appearance",
            run: "click",
        },
        {
            trigger:
                ".snippet-option-WebsiteLevelColor [data-customize-website-variable=\"'slideout_slide_hover'\"]:not(:visible)",
            content: "Set Slideout effect to Slide Hover",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Scroll to footer",
            trigger: ":iframe #footer",
            run() {
                const iframeDocumentEl = document.querySelector(".o_iframe").contentDocument.documentElement;
                iframeDocumentEl.scrollTo({ top: iframeDocumentEl.scrollHeight });
            },
        },
        {
            content: "The footer column should appear",
            trigger: ":iframe #footer .container > .row > div:contains('Useful Links'):visible",
        },
    ],
);
