import {
    clickOnEditAndWaitEditModeInTranslatedPage,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

/**
 * This tour is about delayed translations with custom snippets:
 *
 * -> go to edit mode
 * -> drag a banner into page content
 * -> customize banner (set text)
 * -> save
 * -> go to second language
 * -> enter translate mode
 * -> change the translation
 * -> back to normal edit
 * -> save banner as custom snippet
 * -> remove the banner
 * -> add an unrelated snippet
 * -> add the custom snippet into the page
 * -> save
 * -> go to second language
 * -> check the last translated version is kept
 * -> enter translate mode
 * -> check the custom snippet got the translation from the user
 */

registerWebsitePreviewTour(
    "delayed_translations_with_custom_snippet",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_banner", name: "Banner", groupName: "Intro" }),
        {
            content: "Customize snippet",
            trigger: ":iframe #wrapwrap .s_banner h1",
            run: "editor Test",
        },
        ...clickOnSave(),
        {
            content: "Switch language",
            trigger: ":iframe a.js_change_lang[data-url_code=pa_GB]",
            run: "click",
        },
        {
            content: "Wait the language has changed.",
            trigger: ":iframe header.o_top_fixed_element nav li:contains(parseltongue)",
        },
        {
            content: "Open dropdown edit",
            trigger: "button.o-website-btn-custo-primary",
            run: "click",
        },
        {
            content: "Enter translate mode",
            trigger: ".o_translate_website_dropdown_item",
            run: "click",
        },
        {
            content: "Close color code dialog",
            trigger: ".modal button:contains(Ok, never show me this again)",
            run: "click",
        },
        {
            content: "Customize translation",
            trigger: ":iframe #wrapwrap .s_banner h1 span",
            run: "editor Translated",
        },
        ...clickOnSave(),
        ...clickOnEditAndWaitEditModeInTranslatedPage(),
        {
            content: "Select banner",
            trigger: ":iframe #wrapwrap .s_banner h1",
            run: "click",
        },
        {
            content: "Save custom snippet",
            trigger: "div[data-container-title='Banner'] .oe_snippet_save",
            run: "click",
        },
        {
            content: "Confirm save",
            trigger: ".modal-dialog button:contains('Save')",
            run: "click",
        },
        {
            content: "Remove original snippet from page",
            trigger: "div[data-container-title='Banner'] .oe_snippet_remove",
            run: "click",
        },
        ...insertSnippet({ id: "s_cover", name: "Cover", groupName: "Intro" }),
        ...insertSnippet({ customID: "s_banner", name: "Custom Banner", groupName: "Custom" }),
        ...clickOnSave(),
        {
            content: "Switch language",
            trigger: ":iframe a.js_change_lang[data-url_code=pa_GB]",
            run: "click",
        },
        {
            content: "Wait the language has changed.",
            trigger: ":iframe header.o_top_fixed_element nav li:contains(parseltongue)",
        },
        {
            content: "Verify last valid translation is still served",
            trigger: ":iframe #wrap:has(.s_banner:contains(Translated)):not(:has(.s_cover))",
        },
        {
            content: "Open dropdown edit",
            trigger: "button.o-website-btn-custo-primary",
            run: "click",
        },
        {
            content: "Enter translate mode",
            trigger: ".o_translate_website_dropdown_item",
            run: "click",
        },
        {
            content: "Verify the custom snippet got the translation",
            trigger: ":iframe #wrap:has(.s_banner:contains(Translated)):has(.s_cover)",
        },
    ]
);
