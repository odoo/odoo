import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
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
        {
            content: "Check that the highlight options were displayed",
            trigger: ".o_popover .o_text_highlight_underline",
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
            trigger: ".o_menu_systray button:contains('Edit').dropdown-toggle",
            run: "click",
        },
        {
            content: "Enable translation",
            trigger: ".o_translate_website_dropdown_item",
            run: "click",
        },
        {
            content: "Close the dialog",
            trigger: ".modal-footer .btn-secondary",
            run: "click",
        },
        // Select the highlighted text content.
        selectFullText(
            "snippet highlighted text content",
            "#wrap .s_text_block p:last .o_text_highlight"
        ),
        ...clickToolbarButton(
            "second text block in the snippet",
            "#wrap .s_text_block p:last",
            "Apply highlight",
            true
        ),
        {
            content: "Check that the highlight options were displayed",
            trigger: ".o_popover button#highlightPicker",
            run: "click",
        },
        {
            trigger: ".o_popover .o_text_highlight_jagged",
            run: "click",
        },
        // Select the animated text content.
        selectFullText("animated text content", "#wrap .s_text_block p:first"),
        ...clickToolbarButton(
            "first text block in the snippet",
            "#wrap .s_text_block p",
            "Animate Text",
            true
        ),
        {
            content: "Check that the animate options were displayed",
            trigger: ".o_popover .o_animate_text_popover",
            run: "click",
        },
        // Select a text content without any option.
        selectFullText("text content without any option", "footer .s_text_block p:first span"),
        ...clickToolbarButton(
            "second text block in the snippet",
            "#wrap .s_text_block p:last",
            "Apply highlight",
            true
        ),
        {
            content:"Check that all text options are removed",
            trigger: ".popover:not(:has(.o_animate_text_popover)) button#highlightPicker",
        },
        selectFullText("highlighted text content again", "#wrap .s_text_block p:last .o_text_highlight"),
        ...clickToolbarButton(
            "second text block in the snippet",
            "#wrap .s_text_block p:last",
            "Apply highlight",
            true
        ),
        {
            content: "Check that only the highlight options are displayed",
            trigger:
                ".popover:not(:has(.o_animate_text_popover)) button#highlightPicker",
        },
        ...clickOnSave(),
        {
            content: "Check that the highlight effect was correctly translated",
            trigger:
                ":iframe .s_text_block:has(.o_text_highlight_jagged)",
        },
    ]
);
