import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
    selectElementInWeSelectWidget,
    selectFullText,
    clickToolbarButton,
} from "@website/js/tours/tour_utils";

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
        ...clickToolbarButton(
            "first text block in the snippet",
            "#wrap .s_text_block p",
            "Animate Text",
            true
        ),
        ...clickToolbarButton(
            "second text block in the snippet",
            "#wrap .s_text_block p:last",
            "Apply highlight",
            true
        ),
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
        selectFullText("snippet highlighted text content", "#wrap .s_text_block p:last .o_text_highlight"),
        {
            content: "Check that the highlight options were displayed",
            trigger: "#toolbar we-select[data-name=text_highlight_opt]",
        },
        ...selectElementInWeSelectWidget("text_highlight_opt", "Jagged"),
        // Select the animated text content.
        selectFullText("animated text content", "#wrap .s_text_block p:first .o_animated_text"),
        {
            content:
                "Check that the animation options are displayed and highlight options are no longer visible",
            trigger:
                "#toolbar:not(:has(.snippet-option-TextHighlight)) .snippet-option-WebsiteAnimate",
        },
        // Select a text content without any option.
        selectFullText("text content without any option", "footer .s_text_block p:first span"),
        {
            content: "Check that all text options are removed",
            trigger:
                "#toolbar:not(:has(.snippet-option-TextHighlight, .snippet-option-WebsiteAnimate))",
        },
        // Select the highlighted text content again.
        selectFullText("highlighted text content again", "#wrap .s_text_block p:last .o_text_highlight"),
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
