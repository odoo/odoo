/** @odoo-module */

import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const selectText = (selector) => ({
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
});

registerWebsitePreviewTour(
    "fullscreen_slide_text_highlights",
    {
        url: "/slides",
    },
    () => [
        {
            trigger: ':iframe a:contains("Basics of Gardening - Test")',
            run: "click",
        },
        {
            trigger: ':iframe a:contains("Article test")',
            run: "click",
        },
        {
            content:
                "The chatter of the inactive discuss tab must not boot on its own, so that " +
                "its bundle can never load in the middle of the edit mode startup",
            trigger: ":iframe #discuss .o_portal_chatter:hidden:not(:has(#chatterRoot))",
        },
        ...clickOnEditAndWaitEditMode(),
        selectText(".s_text_block > p"),
        {
            content: "Expand the text editor toolbar",
            trigger: 'button[name="expand_toolbar"]',
            run: "click",
        },
        {
            content: "Click on the 'Highlight Effects' button to show the listing",
            trigger: "button.o-select-highlight",
            run: "click",
        },
        {
            content: "Click on the first highlight effect proposed to activate it",
            trigger: "span.o_text_highlight",
            run: "click",
        },
        {
            content: "Check that the highlight was applied",
            trigger: ":iframe .o_wslides_lesson_content_type p span.o_text_highlight > svg",
        },
        {
            content: "Check that the highlight was applied",
            trigger:
                ":iframe .o_wslides_lesson_content_type p span.o_text_highlight > svg.o_text_highlight_svg",
        },
        ...clickOnSave(),
        {
            content: "Reveal the discuss tab",
            trigger: ":iframe a[href='#discuss']",
            run: "click",
        },
        {
            content:
                "Revealing the tab must boot the chatter that stayed dormant until now, so " +
                "that deferring the boot never costs the user the chatter itself",
            trigger: ":iframe #chatterRoot:shadow .o-mail-Chatter",
        },
        {
            content: "Click on the fullscreen button",
            trigger: ':iframe #wrapwrap a[aria-label="Fullscreen"]',
            run: "click",
        },
        {
            content: "Wait for fullscreen",
            trigger: ':iframe #wrapwrap a[title="Exit Fullscreen"]',
        },
        {
            content: "Check that the highlight was applied in fullscreen",
            trigger:
                ":iframe .o_wslides_fs_content p span.o_text_highlight > svg.o_text_highlight_svg",
        },
    ]
);
