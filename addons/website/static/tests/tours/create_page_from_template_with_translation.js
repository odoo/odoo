import { clickOnSave, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

function switchLanguage(language) {
    return [
        {
            content: "Ensure was in other language",
            trigger: `:iframe .o_header_language_selector button.dropdown-toggle:not(:contains(${language}))`,
        },
        {
            content: "Open language dropdown",
            trigger: `:iframe .o_header_language_selector button.dropdown-toggle`,
            run: "click",
        },
        {
            content: "Select language",
            trigger: `:iframe .o_header_language_selector .js_change_lang:contains(${language})`,
            run: "click",
        },
        {
            content: "Wait until target page is loaded",
            trigger: `:iframe .o_header_language_selector button.dropdown-toggle:contains(${language})`,
            timeout: 50000,
        },
    ];
}

registerWebsitePreviewTour("create_page_from_template_with_translation", {}, () => [
    { trigger: ':iframe [is-ready="true"]' },
    ...switchLanguage("Français"),
    {
        content: "Open new page menu",
        trigger: ".o_menu_systray .o_new_content_container button",
        run: "click",
    },
    {
        content: "Click on new page",
        trigger: "button.o_new_content_element",
        run: "click",
    },
    {
        content: "Click on custom group",
        trigger: "button[data-id=custom]",
        run: "click",
    },
    {
        content: "Select the page template",
        // The button is hidden until the pointer hovers the parent div, so look for non-visible elements
        trigger:
            ".o_page_template.o_ready button:not(:visible):contains('Translated page template')",
        run: "click",
    },
    {
        content: "Name the page",
        trigger: "label:contains(Page Title) + * input",
        run: `fill Test Page`,
    },
    {
        content: "Create the page",
        trigger: "button:contains(Create)",
        run: "click",
    },

    {
        content: "Ensure it switch to default language",
        trigger: `:iframe .o_header_language_selector button.dropdown-toggle:contains(English)`,
    },
    {
        content: "Ensure content is in default language",
        trigger: `:iframe #wrap :text("Some content in English")`,
    },
    ...clickOnSave(),

    ...switchLanguage("Français"),
    {
        content: "Ensure content is in French",
        trigger: `:iframe #wrap :text("Du contenu en français")`,
    },
]);
