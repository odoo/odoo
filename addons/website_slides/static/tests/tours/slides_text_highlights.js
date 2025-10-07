/** @odoo-module */

import { registry } from "@web/core/registry";
import wTourUtils from "@website/js/tours/tour_utils";

const selectText = (selector) => {
    return {
        content: "Select some text content",
        trigger: `iframe ${selector}`,
        run() {
            const iframeDOC = document.querySelector(".o_iframe").contentDocument;
            const range = iframeDOC.createRange();
            const selection = iframeDOC.getSelection();
            range.selectNodeContents(this.$anchor[0]);
            selection.removeAllRanges();
            selection.addRange(range);
            this.$anchor[0].click();
        },
    };
};

registry.category("web_tour.tours").add("fullscreen_slide_text_highlights", {
    test: true,
    edition: true,
    steps: () => [
// registerWebsitePreviewTour step to wait for the edit mode
{
    content: "Wait for the edit mode to be started",
    trigger: ".o_website_preview.editor_enable.editor_has_snippets",
    timeout: 30000,
    auto: true,
    run: () => {}, // It's a check
},
selectText("#wrapwrap #wrap .s_text_block > p"),
{
    content: "Click on the 'Highlight Effects' button to activate the option",
    trigger: "div.o_we_text_highlight",
}, {
    content: "Check that the highlight was applied",
    trigger: "iframe .s_text_block p span.o_text_highlight > .o_text_highlight_item > svg:has(.o_text_highlight_path_underline)",
    isCheck: true,
},
...wTourUtils.clickOnSave(),
{
    content: "Click on the fullscreen button",
    trigger: 'iframe #wrapwrap a[aria-label="Fullscreen"]',
}, {
    content: "Check that the highlight was applied",
    trigger: "iframe .s_text_block p span.o_text_highlight > .o_text_highlight_item > svg:has(.o_text_highlight_path_underline)",
    isCheck: true,
},
]});
