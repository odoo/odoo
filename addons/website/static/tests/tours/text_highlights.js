/** @odoo-module */

import {
    insertSnippet,
    registerWebsitePreviewTour,
    selectElementInWeSelectWidget,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("text_highlights", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({
        id: "s_cover",
        name: "Cover",
        groupName: "Intro",
    }),
    {
        content: "Select the snippet title",
        trigger: ":iframe .s_cover h1",
        run: "dblclick",
    },
    {
        content: "Click on the 'Highlight Effects' button to activate the option",
        trigger: "div.o_we_text_highlight",
        run: "click",
    },
    {
        content: "Check that the highlight was applied",
        trigger: ":iframe .s_cover h1 span.o_text_highlight > .o_text_highlight_item > svg:has(.o_text_highlight_path_underline)",
    },
    {
        content: "Check that the highlights grid was displayed",
        trigger: "we-select[data-name=text_highlight_opt] we-toggler.active",
    },
    {
        content: "Disable the highlight effect",
        trigger: "div.o_we_text_highlight",
        run: "click",
    },
    {
        content: "Check that the highlight was disabled for the title",
        trigger: ":iframe .s_cover:not(:has(.o_text_highlight))",
    },
    {
        // On muti-line text, the highlight effect is added on every detected
        // line (using the `.o_text_highlight_item` span).
        content: "Update and select the snippet paragraph content",
        trigger: ":iframe .s_cover p",
        run() {
            const iframeDOC = document.querySelector(".o_iframe").contentDocument;
            const firstLine = document.createElement("strong");
            firstLine.textContent = "Text content line A";
            const secondLine = document.createElement("i");
            secondLine.textContent = "Text content line B";
            this.anchor.replaceChildren(firstLine, document.createElement("br"), secondLine);
            // Select the whole content.
            const range = iframeDOC.createRange();
            const selection = iframeDOC.getSelection();
            range.selectNodeContents(this.anchor);
            selection.removeAllRanges();
            selection.addRange(range);
        },
    },
    {
        content: "Add the highlight effect on the muti-line text",
        trigger: "div.o_we_text_highlight",
        run: "click",
    },
    {
        content: "Check if the text was correctly updated",
        trigger: ":iframe .o_text_highlight_underline:has(span:contains(Text content line A) + br + span:contains(Text content line B))",
    },
    ...selectElementInWeSelectWidget("text_highlight_opt", "Jagged").slice(1), // The select is already opened
    {
        trigger: ":iframe .o_text_highlight_item:has(.o_text_highlight_path_jagged):nth-child(3)",
    },
    {
        content: "When changing the text highlight, we only replace the highlight SVG with a new drawn one",
        trigger: ":iframe .o_text_highlight_item:has(.o_text_highlight_path_jagged):nth-child(1)",
    },
    {
        content: "Disable the highlight effect",
        trigger: "div.o_we_text_highlight",
        run: "click",
    },
    {
        content: "Check if the original DOM structure was restored",
        trigger: ":iframe .s_cover p:has(strong:contains(Text content line A) + br + i:contains(Text content line B))",
    },
]);
