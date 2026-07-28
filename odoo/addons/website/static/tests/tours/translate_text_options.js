/** @odoo-module **/

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

wTourUtils.registerWebsitePreviewTour(
    "translate_text_options",
    {
        url: "/",
        test: true,
        edition: true,
    },
    () => [
        wTourUtils.dragNDrop({
            id: "s_text_block",
            name: "Text",
        }),
        {
            content: "Select the first text block in the snippet",
            trigger: "iframe #wrap .s_text_block p:first",
            run: "dblclick",
        },
        {
            content: "Click on the 'Animate Text' button to activate the option",
            trigger: "div.o_we_animate_text",
        },
        {
            content: "Select the second text block in the snippet",
            trigger: "iframe #wrap .s_text_block p:last",
            run: "dblclick",
        },
        {
            content: "Click on the 'Highlight Effects' button to activate the option",
            trigger: "div.o_we_text_highlight",
        },
        ...wTourUtils.clickOnSave(),
        {
            content: "Change the language to French",
            trigger: 'iframe .js_language_selector .js_change_lang[data-url_code="fr"]',
        },
        {
            content: "Enable translation",
            trigger: ".o_translate_website_container a",
        },
        {
            content: "Close the dialog",
            trigger: ".modal-footer .btn-secondary",
        },
        // Select the highlighted text content.
        selectText("#wrap .s_text_block p:last .o_text_highlight"),
        {
            content: "Check that the highlight options were displayed",
            trigger: "#toolbar we-select[data-name=text_highlight_opt]",
            isCheck: true,
        },
        ...wTourUtils.selectElementInWeSelectWidget("text_highlight_opt", "Jagged"),
        // Select the animated text content.
        selectText("#wrap .s_text_block p:first .o_animated_text"),
        {
            content:
                "Check that the animation options are displayed and highlight options are no longer visible",
            trigger:
                "#toolbar:not(:has(.snippet-option-TextHighlight)) .snippet-option-WebsiteAnimate",
            isCheck: true,
        },
        // Select a text content without any option.
        selectText("footer .s_text_block p:first span"),
        {
            content: "Check that all text options are removed",
            trigger:
                "#toolbar:not(:has(.snippet-option-TextHighlight, .snippet-option-WebsiteAnimate))",
            isCheck: true,
        },
        // Select the highlighted text content again.
        selectText("#wrap .s_text_block p:last .o_text_highlight"),
        {
            content: "Check that only the highlight options are displayed",
            trigger:
                "#toolbar:not(:has(.snippet-option-WebsiteAnimate)) .snippet-option-TextHighlight",
            isCheck: true,
        },
        ...wTourUtils.clickOnSave(),
        {
            content: "Check that the highlight effect was correctly translated",
            trigger:
                "iframe .s_text_block .o_text_highlight:has(.o_text_highlight_item:has(.o_text_highlight_path_jagged))",
            isCheck: true,
        },
    ]
);
