/** @odoo-module */

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("text_highlights", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: "s_cover",
        name: "Cover",
    }),
    {
        content: "Select the snippet title",
        trigger: "iframe .s_cover h1",
        run: "dblclick",
    },
    {
        content: "Click on the 'Highlight Effects' button to activate the option",
        trigger: "div.o_we_text_highlight",
    },
    {
        content: "Check that the highlight was applied",
        trigger: "iframe .s_cover h1 span.o_text_highlight > .o_text_highlight_item > svg:has(.o_text_highlight_path_underline)",
        isCheck: true,
    },
    {
        content: "Disable the highlight effect",
        trigger: "div.o_we_text_highlight",
    },
    {
        content: "Check that the highlight was disabled for the title",
        trigger: "iframe .s_cover:not(:has(.o_text_highlight))",
        isCheck: true,
    },
    {
        // On muti-line text, the highlight effect is added on every detected
        // line (using the `.o_text_highlight_item` span).
        content: "Update and select the snippet paragraph content",
        trigger: "iframe .s_cover p",
        run() {
            const iframeDOC = document.querySelector(".o_iframe").contentDocument;
            const firstLine = document.createElement("strong");
            firstLine.textContent = "Text content line A";
            const secondLine = document.createElement("i");
            secondLine.textContent = "Text content line B";
            this.$anchor[0].replaceChildren(firstLine, document.createElement("br"), secondLine);
            // Select the whole content.            
            const range = iframeDOC.createRange();
            const selection = iframeDOC.getSelection();
            range.selectNodeContents(this.$anchor[0]);
            selection.removeAllRanges();
            selection.addRange(range);
        },
    },
    {
        content: "Add the highlight effect on the muti-line text",
        trigger: "div.o_we_text_highlight",
    },
    {
        content: "Check if the text was correctly updated",
        trigger: "iframe .s_cover span.o_text_highlight:has(.o_text_highlight_item:has(.o_text_highlight_path_underline) + br + .o_text_highlight_item:has(.o_text_highlight_path_underline))",
        isCheck: true,
    },
    ...wTourUtils.selectElementInWeSelectWidget("text_highlight_opt", "Jagged"),
    {
        content: "When changing the text highlight, we only replace the highlight SVG with a new drawn one",
        trigger: "iframe .s_cover span.o_text_highlight:has(.o_text_highlight_item:has(.o_text_highlight_path_jagged) + br + .o_text_highlight_item:has(.o_text_highlight_path_jagged))",
        isCheck: true,
    },
    {
        content: "Disable the highlight effect",
        trigger: "div.o_we_text_highlight",
    },
    {
        content: "Check if the original DOM structure was restored",
        trigger: "iframe .s_cover p:has(strong:contains(Text content line A) + br + i:contains(Text content line B))",
        isCheck: true,
    },
]);
