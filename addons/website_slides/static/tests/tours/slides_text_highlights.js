/** @odoo-module */

import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

const selectText = (selector) => {
    return {
        content: "Select some text content",
        trigger: "iframe",
        run() {
            const iframeWindow = this.anchor.contentWindow;
            const iframeDocument = iframeWindow.document;
            const p = iframeDocument.querySelector(selector);
            p.click();
            const selection = iframeWindow.getSelection();
            const range = iframeDocument.createRange();
            range.selectNodeContents(p);
            selection.removeAllRanges();
            selection.addRange(range);
        },
    };
};

registerWebsitePreviewTour('fullscreen_slide_text_highlights', {
    url: "/slides",
}, () => [
        {
            trigger: ':iframe a:contains("Basics of Gardening - Test")',
            run: "click",
        },
        {
            trigger: ':iframe a:contains("Article test")',
            run: "click",
        },
        {
            trigger: ':iframe span:contains("Exit Fullscreen")',
            run: "click",
        },
        ...clickOnEditAndWaitEditMode(),
        selectText(".s_text_block > p"),
        {
            content: "Click on the 'Highlight Effects' button to activate the option",
            trigger: "div.o_we_text_highlight",
            run: "click",
        },
        {
            content: "Check that the highlight was applied",
            trigger: ":iframe .s_text_block p span.o_text_highlight > .o_text_highlight_item > svg:has(.o_text_highlight_path_underline)",
        },
        ...clickOnSave(),
        {
            content: "Click on the fullscreen button",
            trigger: ':iframe #wrapwrap a[aria-label="Fullscreen"]',
        }, {
            content: "Check that the highlight was applied in fullscreen",
            trigger: ":iframe .s_text_block p span.o_text_highlight > .o_text_highlight_item > svg:has(.o_text_highlight_path_underline)",
        },
    ],
);
