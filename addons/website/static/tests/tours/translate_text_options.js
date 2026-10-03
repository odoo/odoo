import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
    selectFullText,
    clickToolbarButton,
    expandToolbar,
    openEffectsPanelSection,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "translate_text_options",
    {
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
            "Text effects",
            true
        ),
        ...openEffectsPanelSection("animateText"),
        {
            content: "Open the animation choices",
            trigger: ".o_animate_text_section [data-label='Animation'] .o_hb_select_toggle",
            run: "click",
        },
        {
            content: "Animate the selected text",
            trigger: ".o-dropdown--menu .o-dropdown-item:contains('On Appearance')",
            run: "click",
        },
        selectFullText("second text block in the snippet", "#wrap .s_text_block p:last"),
        {
            content: "Wait for the toolbar of the second text block",
            // The toolbar of the animated block lingers until the next render,
            // and a panel opened from it is destroyed with it.
            trigger: ".o-we-toolbar[data-namespace]:not(:has(.o-select-effects.active))",
        },
        expandToolbar(),
        {
            content: "Open the text effects of the second text block",
            trigger: ".o-we-toolbar button.o-select-effects:not(.active)",
            run: "click",
        },
        ...openEffectsPanelSection("highlight"),
        {
            content: "Open the highlight shapes",
            trigger: ".o_popover #highlightPicker",
            run: "click",
        },
        {
            content: "Apply underline highlight option from highlight options",
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
        // Select the highlighted text content and check highlight options were displayed.
        selectFullText(
            "snippet highlighted text content",
            "#wrap .s_text_block p:last .o_text_highlight"
        ),
        expandToolbar(),
        {
            content: "Check that the text effects are active and open them",
            trigger: ".o-we-toolbar button.o-select-effects.active",
            run: "click",
        },
        ...openEffectsPanelSection("highlight"),
        {
            content: "Open highlight options picker",
            trigger: ".o_popover button#highlightPicker",
            run: "click",
        },
        {
            content: "Change highlight to jagged",
            trigger: ".o_popover .o_text_highlight_jagged",
            run: "click",
        },
        // Select the animated text content and check animate options were displayed.
        selectFullText("animated text content", "#wrap .s_text_block p:first span"),
        expandToolbar(),
        {
            content: "Check that the text effects are active",
            trigger: ".o-we-toolbar button.o-select-effects.active",
        },
        // Select a text content without any option.
        selectFullText("text content without any option", "footer .s_text_block p:first span"),
        expandToolbar(),
        {
            content: "Check that no text effect is active",
            trigger: ".o-we-toolbar button.o-select-effects:not(.active)",
        },
        selectFullText(
            "highlighted text content again",
            "#wrap .s_text_block p:last .o_text_highlight"
        ),
        expandToolbar(),
        {
            content: "Open the text effects",
            trigger: ".o-we-toolbar button.o-select-effects.active",
            run: "click",
        },
        {
            content: "Check that only the highlight is applied",
            trigger:
                ".o-we-effects-section-active[data-section='highlight'] ~ .o-we-effects-section[data-section='animateText']:not(.o-we-effects-section-active)",
        },
        ...clickOnSave(),
        {
            content: "Check that the highlight effect was correctly translated",
            trigger: ":iframe .s_text_block:has(.o_text_highlight_jagged)",
        },
    ]
);
