import { editorsWeakMap } from "@html_editor/../tests/tours/helpers/editor";
import {
    clickToolbarButton,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

function applyHighlight(target, targetName, highlight) {
    return [
        ...clickToolbarButton(targetName, target, "Apply highlight", true),
        {
            content: "Check that the highlights grid was displayed",
            trigger: ".o_popover .o_text_highlight",
        },
        {
            content: "Select the highlight effect",
            trigger: `.o_popover span.o_text_highlight_${highlight}`,
            run: "click",
        },
    ];
}

function countLines(el) {
    const lines = new Set();
    const walker = el.ownerDocument.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const range = el.ownerDocument.createRange();
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        if (!node.textContent.trim() || node.parentElement.closest("svg")) {
            continue;
        }
        range.selectNodeContents(node);
        for (const rect of range.getClientRects()) {
            lines.add(Math.round(rect.top));
        }
    }
    return lines.size;
}

registerWebsitePreviewTour(
    "text_highlights",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_title",
            name: "Title",
            groupName: "Text",
        }),
        ...insertSnippet({
            id: "s_cover",
            name: "Cover",
            groupName: "Intro",
        }),
        {
            content: "Set a long page title",
            trigger: ":iframe .s_title h2",
            run: "editor This is an example of an unusually long title that exists purely to test multi-line wrapping",
        },
        ...applyHighlight(".s_title h2", "page title", "underline"),
        {
            content: "Check that the highlights was correctly applied",
            trigger: ":iframe .s_title .o_text_highlight:has(svg.o_text_highlight_svg)",
            run() {
                if (
                    this.anchor.querySelectorAll("svg").length !==
                    countLines(this.anchor)
                ) {
                    throw new Error(
                        "The highlight svgs are not correctly applied to text lines",
                    );
                }
            },
        },
        ...applyHighlight(".s_cover h1", "snippet title", "underline"),
        {
            content: "Check that the highlight was applied",
            trigger:
                ":iframe .s_cover h1 span.o_text_highlight_underline svg.o_text_highlight_svg",
        },
        {
            content: "Disable the highlight effect",
            trigger: ".o_popover button[title='Reset']",
            run: "click",
        },
        {
            content: "Check that the highlight was disabled for the title",
            trigger: ":iframe .s_cover:not(:has(.o_text_highlight))",
        },
        {
            content: "Update and select the snippet paragraph content",
            trigger: ":iframe .s_cover p",
            run() {
                const iframeDOC = document.querySelector(
                    ".o_iframe_container > iframe",
                ).contentDocument;
                const firstLine = document.createElement("strong");
                firstLine.textContent = "Text content line A";
                const secondLine = document.createElement("i");
                secondLine.textContent = "Text content line B";
                this.anchor.replaceChildren(
                    firstLine,
                    document.createElement("br"),
                    secondLine,
                );
                const editor = editorsWeakMap.get(this.anchor.ownerDocument);
                editor.shared.history.addStep();
                const range = iframeDOC.createRange();
                const selection = iframeDOC.getSelection();
                range.selectNodeContents(this.anchor);
                selection.removeAllRanges();
                selection.addRange(range);
            },
        },
        {
            content: "Check that the highlights grid was displayed",
            trigger: ".o_popover .o_text_highlight",
        },
        {
            content: "Select the highlight effect",
            trigger: ".o_popover span.o_text_highlight_underline",
            run: "click",
        },
        {
            content: "Check if the text was correctly updated",
            trigger:
                ":iframe span.o_text_highlight_underline:contains(Text content line A) + br + span.o_text_highlight_underline:contains(Text content line B)",
        },
        {
            content: "Click on highlight picker to change the highlight effect",
            trigger: ".o_popover #highlightPicker",
            run: "click",
        },
        {
            content: "Check that the highlights grid was displayed",
            trigger: ".o_popover .o_text_highlight",
        },
        {
            content: "Change the highlight effect",
            trigger: ".o_popover span.o_text_highlight_jagged",
            run: "click",
        },
        {
            content: "Check if the text was correctly updated",
            trigger:
                ":iframe span.o_text_highlight_jagged:contains('Text content line A') + br + span.o_text_highlight_jagged:contains('Text content line B')",
        },
        {
            content: "Disable the highlight effect",
            trigger: ".o_popover button[title='Reset']",
            run: "click",
        },
        {
            content: "Check if the original DOM structure was restored",
            trigger:
                ":iframe .s_cover p:has(strong:contains(Text content line A) + br + i:contains(Text content line B))",
        },
    ],
);
