import {
    clickOnEditAndWaitEditModeInTranslatedPage,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

function changeLanguageAndOpenTranslateMode() {
    return [
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
    ];
}

registerWebsitePreviewTour(
    "translate_select_element",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_title_form",
            name: "Title - Form",
            groupName: "Contact & Forms",
        }),
        {
            content: "Click on the form to select it",
            trigger: ":iframe .s_website_form form",
            run: "click",
        },
        {
            content: "Click on add field button",
            trigger: ".options-container-header button:contains('+ Field')",
            run: "click",
        },
        {
            content: "Select field type as Selection",
            trigger: "[data-container-title=Field] [data-action-value=many2one]:not(:visible)",
            run: "click",
        },
        ...clickOnSave(),
        ...changeLanguageAndOpenTranslateMode(),
        {
            content: "Edit the first option translation",
            trigger: ":iframe .o_translation_select span:contains('Option 1')",
            run({ anchor }) {
                anchor.textContent = "Première Option";
            },
        },
        ...clickOnSave(),
        ...clickOnEditAndWaitEditModeInTranslatedPage(),
        {
            content: "Click on the selection field",
            trigger: ":iframe .s_website_form_field:last",
            run: "click",
        },
        {
            content: "Edit the second option and click on another one to apply the edit",
            trigger: "input.o-hb-input-base[data-id='1']",
            run: "edit(Second option) && click input.o-hb-input-base[data-id='0']",
        },
        ...clickOnSave(),
        {
            content: "Change the language to French",
            trigger: ':iframe .js_language_selector .js_change_lang[data-url_code="fr"]',
            run: "click",
        },
        ...changeLanguageAndOpenTranslateMode(), // Open the delayed translation
        {
            content: "The first option should have kept its translation",
            trigger:
                ":iframe .o_translation_select span[data-oe-translation-state=translated]:contains('Première Option')",
        },
        {
            content: "The second option should have changed text",
            trigger:
                ":iframe .o_translation_select span[data-oe-translation-state=to_translate]:contains('Second option')",
        },
    ]
);
