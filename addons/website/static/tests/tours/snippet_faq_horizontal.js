/** @odoo-module */

import {
    checkIfVisibleOnScreen,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "snippet_faq_horizontal",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_faq_horizontal", name: "Topics List", groupName: "Text" }),
        ...clickOnSnippet({ id: "s_faq_horizontal", name: "Topics List" }),
        {
            content: "Wait for Add New button to appear and mock scrollTo",
            trigger: "we-button:has(div:contains('Add New'))",
            async run() {
                const iframeDocumentEl = document.querySelector(".o_iframe").contentDocument.documentElement;
                // Mock scrollTo to bypass the animation delay
                iframeDocumentEl.scrollTo = ({ top }) => {
                    iframeDocumentEl.scrollTop = top;
                };
            },
        }, {
            content: "Click on Add New",
            trigger: "we-button:has(div:contains('Add New'))",
            run: "click",
        },
        checkIfVisibleOnScreen(":iframe .s_faq_horizontal_entry:nth-child(4)"),
    ],
);
