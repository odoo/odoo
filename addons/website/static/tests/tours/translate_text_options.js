/** @odoo-module **/

import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
    selectElementInWeSelectWidget,
} from "@website/js/tours/tour_utils";

const selectText = (selector) => {
    return {
        content: "Select some text content",
        trigger: `:iframe ${selector}`,
        run() {
            const iframeDOC = document.querySelector(".o_iframe").contentDocument;
            const range = iframeDOC.createRange();
            const selection = iframeDOC.getSelection();
            range.selectNodeContents(this.anchor);
            selection.removeAllRanges();
            selection.addRange(range);
            this.anchor.click();
        },
    };
};

registerWebsitePreviewTour(
    "translate_text_options",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_text_block",
            name: "Text",
            groupName: "Text",
        }),
        {
            content: "Select the first text block in the snippet",
            trigger: ":iframe #wrap .s_text_block p:first",
            run: "dblclick",
        },
        {
            content: "Click on the 'Animate Text' button to activate the option",
            trigger: "div.o_we_animate_text",
            run: "click",
        },
        {
            content: "Select the second text block in the snippet",
            trigger: ":iframe #wrap .s_text_block p:last",
            run: "dblclick",
        },
        {
            content: "Click on the 'Highlight Effects' button to activate the option",
            trigger: "div.o_we_text_highlight",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Change the language to French",
            trigger: ':iframe .js_language_selector .js_change_lang[data-url_code="fr"]',
            run: "click",
        },
        {
            content: "Click edit button",
            trigger: ".o_menu_systray .o_edit_website_container button",
            run: "click",
        },
        {
            content: "Enable translation",
            trigger: ".o_popover .o_translate_website_dropdown_item",
            run: "click",
        },
        {
            content: "Close the dialog",
            trigger: ".modal-footer .btn-secondary",
            run: "click",
        },
        // Select the highlighted text content.
        selectText("#wrap .s_text_block p:last .o_text_highlight"),
        {
            content: "Check that the highlight options were displayed",
            trigger: "#toolbar we-select[data-name=text_highlight_opt]",
        },
        ...selectElementInWeSelectWidget("text_highlight_opt", "Jagged"),
        // Select the animated text content.
        selectText("#wrap .s_text_block p:first .o_animated_text"),
        {
            content:
                "Check that the animation options are displayed and highlight options are no longer visible",
            trigger:
                "#toolbar:not(:has(.snippet-option-TextHighlight)) .snippet-option-WebsiteAnimate",
        },
        // Select a text content without any option.
        selectText("footer .s_text_block p:first span"),
        {
            content: "Check that all text options are removed",
            trigger:
                "#toolbar:not(:has(.snippet-option-TextHighlight, .snippet-option-WebsiteAnimate))",
        },
        // Select the highlighted text content again.
        selectText("#wrap .s_text_block p:last .o_text_highlight"),
        {
            content: "Check that only the highlight options are displayed",
            trigger:
                "#toolbar:not(:has(.snippet-option-WebsiteAnimate)) .snippet-option-TextHighlight",
        },
        ...clickOnSave(),
        {
            content: "Check that the highlight effect was correctly translated",
            trigger:
                ":iframe .s_text_block .o_text_highlight:has(.o_text_highlight_item:has(.o_text_highlight_path_jagged))",
        },
    ]
);
