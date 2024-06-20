/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

const checkNoTranslate = {
    content: "Check there is no translate button",
    trigger: ".o_menu_systray:not(:contains(.o_translate_website_container))",
};
const translate = [{
    content: "Open Edit menu",
    trigger: ".o_menu_systray .o_edit_website_container button",
    run: "click",
}, {
    content: "Click on translate button",
    trigger: ".o_popover .o_translate_website_dropdown_item",
    run: "click",
}];
const closeErrorDialog = [{
    content: "Check has error dialog",
    trigger: "div.o_error_dialog.modal-content",
}, {
    content: "Close error dialog",
    trigger: ".modal-footer button.btn.btn-primary",
    run: "click",
}];
const switchTo = (lang) => {
    return [{
        content: `Switch to ${lang}`,
        trigger: `:iframe .js_change_lang[data-url_code='${lang}']`,
        run: "click",
    }, {
        content: `Wait until ${lang} is applied`,
        trigger: `:iframe html[lang*="${lang}"]`,
    }];
};
const goToMenuItem = [
    wTourUtils.clickOnExtraMenuItem({}, true),
    {
        content: "Navigate to model item page",
        trigger: ":iframe a[href='/test_website/model_item/1']",
        run: "click",
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
        trigger: "#oe_snippets .oe_snippet[name='Banner'].o_disabled",
    },
    ...wTourUtils.clickOnSave(),
    ...switchTo('fr'),
    ...translate,
    ...closeErrorDialog,
    ...switchTo('en'),
    // Model item
    ...goToMenuItem,
    checkNoTranslate,
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Check icons cannot be dragged",
        trigger: "#oe_snippets .oe_snippet[name='Banner'].o_disabled",
    },
    ...switchTo('fr'),
    ...translate,
    ...closeErrorDialog,
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
        trigger: "#oe_snippets .oe_snippet[name='Banner'].o_disabled",
    },
    ...wTourUtils.clickOnSave(),
    ...switchTo('fr'),
    ...translate,
    ...closeErrorDialog,
    ...switchTo('en'),
    // Model item
    ...goToMenuItem,
    checkNoTranslate,
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Check icons can be dragged",
        trigger: "#oe_snippets .oe_snippet[name='Banner']:not(.o_disabled)",
    },
    {
        content: "Drag the banner block",
        trigger: `#oe_snippets .oe_snippet[name="Banner"].o_we_draggable .oe_snippet_thumbnail:not(.o_we_already_dragging)`,
        run: "drag_and_drop :iframe [data-oe-expression='record.website_description']",
    },
    {
        content: "Change name",
        trigger: ":iframe [data-oe-expression='record.name']",
        run: "editor New value",
    },
    ...wTourUtils.clickOnSave(),
    ...switchTo('fr'),
    ...translate,
    {
        content: "Close the dialog",
        trigger: '.modal-footer .btn-primary',
        run: "click",
    },
    {
        content: "Translate name",
        trigger: ":iframe [data-oe-expression='record.name']",
        run: "editor Nouvelle valeur",
    },
    {
        content: "Translate some banner text",
        trigger: ":iframe [data-oe-expression='record.website_description'] strong.o_default_snippet_text",
        run: "editor Facilement.",
    },
    ...wTourUtils.clickOnSave(),
]);
