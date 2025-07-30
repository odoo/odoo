/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

const checkNoTranslate = {
    content: "Check there is no translate button",
    trigger: ".o_menu_systray:not(:contains(.o_translate_website_container))",
    isCheck: true,
};
const translate = {
    content: "Click on translate button",
    trigger: ".o_menu_systray .o_translate_website_container a",
};
const closeErrorDialog = {
    content: "Close error dialog",
    extra_trigger: "div.o_error_dialog.modal-content",
    trigger: ".modal-footer button.btn.btn-primary",
    // Not using implicit command so that final step does not get skipped.
    run: "click",
};
const switchTo = (lang) => {
    return {
        content: `Switch to ${lang}`,
        trigger: `iframe .js_change_lang[data-url_code='${lang}']`,
    };
};
const goToMenuItem = [
    wTourUtils.clickOnExtraMenuItem({}, true),
    {
        content: "Navigate to model item page",
        trigger: "iframe a[href='/test_website/model_item/1']",
    },
];

wTourUtils.registerWebsitePreviewTour('test_restricted_editor_only', {
    test: true,
    url: '/',
}, () => [
    // Home
    checkNoTranslate,
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Check icons cannot be dragged",
        trigger: "#oe_snippets div[data-oe-thumbnail$='s_banner.svg'].oe_snippet.o_disabled",
        isCheck: true,
    },
    ...wTourUtils.clickOnSave(),
    switchTo('fr'),
    translate,
    closeErrorDialog,
    switchTo('en'),
    // Model item
    ...goToMenuItem,
    checkNoTranslate,
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Check icons cannot be dragged",
        trigger: "#oe_snippets div[data-oe-thumbnail$='s_banner.svg'].oe_snippet.o_disabled",
        isCheck: true,
    },
    switchTo('fr'),
    translate,
    closeErrorDialog,
]);

wTourUtils.registerWebsitePreviewTour('test_restricted_editor_test_admin', {
    test: true,
    url: '/',
}, () => [
    // Home
    checkNoTranslate,
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Check icons cannot be dragged",
        trigger: "#oe_snippets div[data-oe-thumbnail$='s_banner.svg'].oe_snippet.o_disabled",
        isCheck: true,
    },
    ...wTourUtils.clickOnSave(),
    switchTo('fr'),
    translate,
    closeErrorDialog,
    switchTo('en'),
    // Model item
    ...goToMenuItem,
    checkNoTranslate,
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Check icons can be dragged",
        trigger: "#oe_snippets div[data-oe-thumbnail$='s_banner.svg'].oe_snippet:not(.o_disabled)",
        isCheck: true,
    },
    {
        content: "Drag the banner block",
        trigger: `#oe_snippets .oe_snippet[data-oe-thumbnail$='s_banner.svg'] .oe_snippet_thumbnail:not(.o_we_already_dragging)`,
        run: "drag_and_drop_native iframe [data-oe-expression='record.website_description']",
    },
    {
        content: "Change name",
        trigger: "iframe [data-oe-expression='record.name']",
        run: "text New value",
    },
    ...wTourUtils.clickOnSave(),
    switchTo('fr'),
    translate,
    {
        content: "Close the dialog",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "Check that html fields are not content editable when translating",
        trigger: "iframe [data-oe-expression='record.website_description']:not([contenteditable='true'])",
    },
    {
        content: "Translate name",
        trigger: "iframe [data-oe-expression='record.name']",
        run: "text Nouvelle valeur",
    },
    {
        content: "Translate some banner text",
        trigger: "iframe [data-oe-expression='record.website_description'] strong.o_default_snippet_text",
        run: "text Facilement.",
    },
    ...wTourUtils.clickOnSave(),
]);

wTourUtils.registerWebsitePreviewTour('test_restricted_editor_tester', {
    test: true,
    url: '/test_model/1',
}, () => [
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Footer should not be be editable for restricted user",
        trigger: "iframe :has(.o_editable) footer:not(.o_editable):not(:has(.o_editable))",
    },
    ...wTourUtils.clickOnSave(),
]);
