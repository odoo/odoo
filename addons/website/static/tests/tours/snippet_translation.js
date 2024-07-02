/** @odoo-module **/

import { localization } from '@web/core/l10n/localization';
import { translatedTerms } from '@web/core/l10n/translation';
import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour('snippet_translation', {
    url: '/',
    test: true,
}, () => [
    {
        content: "Wait for website preview and check language",
        trigger: ":iframe body #wrapwrap",
        run: () => {
            if (localization.code !== "fu_GB") {
                console.error("the user language is not properly set");
            } else {
                translatedTerms["Save"] = "Save in fu_GB";
            }
        }
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    ...wTourUtils.dragNDrop({name: 'Cover'}),
    {
        content: "Check that contact us contain Parseltongue",
        trigger: ':iframe .s_cover .btn-primary:contains("Contact us in Parseltongue")',
    },
    {
        content: "Check that the save button contains 'in fu_GB'",
        trigger: '.btn[data-action="save"]:contains("Save in fu_GB")',
    },
]);
wTourUtils.registerWebsitePreviewTour('snippet_translation_changing_lang', {
    url: '/',
    test: true,
}, () => [
    {
        content: "Change language to Parseltongue",
        trigger: ':iframe .js_language_selector .btn',
        run: "click",
    },
    {
        content: "Change the language to English",
        trigger: ':iframe .js_language_selector .js_change_lang[data-url_code="en"]',
        run: "click",
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
    ...wTourUtils.clickOnSave(),
    ...wTourUtils.clickOnEditAndWaitEditModeInTranslatedPage(),
    ...wTourUtils.dragNDrop({name: 'Cover'}),
    {
        content: "Check that contact us contain Parseltongue",
        trigger: ':iframe .s_cover .btn-primary:contains("Contact us in Parseltongue")',
    },
]);
