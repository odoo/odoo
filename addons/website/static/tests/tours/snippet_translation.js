/** @odoo-module **/

import { localization } from '@web/core/l10n/localization';
import { translatedTerms } from '@web/core/l10n/translation';
import {
    clickOnEditAndWaitEditMode,
    clickOnEditAndWaitEditModeInTranslatedPage,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('snippet_translation', {
    url: '/',
}, () => [
    {
        content: "Wait for website preview and check language",
        trigger: ":iframe html:has(body:contains(welcome to your)):has(.o_top_fixed_element)",
        run: () => {
            if (localization.code !== "fu_GB") {
                console.error("the user language is not properly set");
            } else {
                translatedTerms["Save"] = "Save in fu_GB";
            }
        }
    },
    ...clickOnEditAndWaitEditMode(),
    ...insertSnippet({id: "s_cover", name: "Cover", groupName: "Intro"}),
    {
        content: "Check that contact us contain Parseltongue",
        trigger: ':iframe .s_cover .btn-outline-secondary:contains("Contact us in Parseltongue")',
    },
    {
        content: "Check that the save button contains 'in fu_GB'",
        trigger: '.btn[data-action="save"]:contains("Save in fu_GB")',
    },
]);
registerWebsitePreviewTour('snippet_translation_changing_lang', {
    url: '/',
}, () => [
    {
        content: "Open dropdown language selector",
        trigger: ':iframe .js_language_selector button',
        run: "click",
    },
    {
        content: "Select the language to Parseltongue",
        trigger: ":iframe .js_language_selector .js_change_lang[data-url_code=pa_GB]",
        run: "click",
    },
    {
        content: "Wait the language has changed.",
        trigger: ":iframe header.o_top_fixed_element nav li:contains(parseltongue)",
    },
    {
        content: "Open dropdown language selector",
        trigger: ':iframe .js_language_selector button',
        run: "click",
    },
    {
        content: "Select the language to English",
        trigger: ":iframe .js_language_selector .js_change_lang[data-url_code=en]",
        run: "click",
    },
    {
        content: "Wait the language has changed.",
        trigger: ":iframe nav li:contains(english)",
    },
    {
        content: "Open Edit dropdown",
        trigger: '.o_edit_website_container button',
        run: "click",
    },
    {
        content: "Enable translation",
        trigger: '.o_translate_website_dropdown_item',
        run: "click",
    },
    {
        content: "Close the dialog",
        trigger: '.modal-footer .btn-primary',
        run: "click",
    },
    ...clickOnSave(),
    ...clickOnEditAndWaitEditModeInTranslatedPage(),
    ...insertSnippet({name: "Cover", id: "s_cover", groupName: "Intro"}),
    {
        content: "Check that contact us contain Parseltongue",
        trigger: ':iframe .s_cover .btn-outline-secondary:contains("Contact us in Parseltongue")',
    },
]);
registerWebsitePreviewTour(
    "snippet_dialog_rtl",
    {
        url: "/",
    },
    () => [
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Select a category snippet to show the snippet dialog",
            trigger: `#snippet_groups .oe_snippet.o_we_draggable[name="Intro"] .oe_snippet_thumbnail`,
            run: "click",
        },
        {
            content: "Check that the snippets preview is in rtl",
            trigger: ".o_dialog :iframe .o_snippets_preview_row[style='direction: rtl;']",
        },
        {
            content: "Check that web.assets_frontend CSS bundle is in rtl",
            trigger:
                ".o_dialog :iframe link[type='text/css'][href*='/web.assets_frontend.rtl']:not(:visible)",
        },
        {
            content: "Check that website.assets_all_wysiwyg_inside CSS bundle is there but not in rtl",
            trigger:
                ".o_dialog :iframe link[type='text/css'][href*='/website.assets_all_wysiwyg_inside']:not([href*='/website.assets_all_wysiwyg_inside.rtl']):not(:visible)",
        },
    ],
);
