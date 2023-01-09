/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour('snippet_translation', {
    url: '/',
    edition: true,
    test: true,
}, [
    wTourUtils.dragNDrop({name: 'Cover'}),
    {
        content: "Check that contact us contain Parseltongue",
        trigger: 'iframe .s_cover .btn-primary:contains("Contact us in Parseltongue")',
        run: () => null, // it's a check
    },
    {
        content: "Check that the save button contains 'in fu_GB'",
        trigger: '.btn[data-action="save"]:contains("Save in fu_GB")',
        run: () => null, // it's a check
    },
]);
wTourUtils.registerWebsitePreviewTour('snippet_translation_changing_lang', {
    url: '/',
    test: true,
}, [
    {
        content: "Change language to Parseltongue",
        trigger: 'iframe .js_language_selector .btn',
    },
    {
        content: "Change the language to English",
        trigger: 'iframe .js_language_selector .js_change_lang[data-url_code="en"]',
    },
    {
        content: "Enable translation",
        trigger: '.o_translate_website_container a',
    },
    {
        content: "Close the dialog",
        trigger: '.modal-footer .btn-primary',
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "Click on edit in master",
        trigger: '.o_edit_website_container a',
    },
    {
        content: "Wait for edit mode to start",
        trigger: '.o_website_preview.editor_enable.editor_has_snippets',
        timeout: '30000',
    },
    wTourUtils.dragNDrop({name: 'Cover'}),
    {
        content: "Check that contact us contain Parseltongue",
        trigger: 'iframe .s_cover .btn-primary:contains("Contact us in Parseltongue")',
        run: () => null, // it's a check
    },
]);
