import {
    clickOnSave,
    clickOnEditAndWaitEditMode,
    clickOnExtraMenuItem,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';
import { stepUtils } from "@web_tour/tour_utils";

const checkNoTranslate = {
    content: "Check there is no translate button",
    trigger: ".o_menu_systray:not(:has(.o-dropdown-toggle-custo)):contains(edit)",
};
const translate = [{
    content: "Open Edit menu",
    trigger: "body .o_menu_systray button.o-website-btn-custo-primary:contains(edit)",
    run: "click",
}, {
    content: "Click on translate button",
    trigger: ".o_popover .o_translate_website_dropdown_item:contains(translate)",
    run: "click",
}];
const closeErrorDialog = [{
    content: "Check has error dialog",
    trigger: ".modal:contains(error) .o_error_dialog.modal-content",
}, {
    content: "Close error dialog",
    trigger: ".modal .modal-footer button.btn.btn-primary",
    run: "click",
}, {
    trigger: "body:not(:has(.modal))",
}];
const switchTo = (lang) => [
    {
        content: `Switch to ${lang}`,
        trigger: `:iframe .js_change_lang[data-url_code='${lang}']`,
        run: "click",
    },
    {
        content: `Wait until ${lang} is applied`,
        trigger: `:iframe html[lang*="${lang}"]`,
    },
    stepUtils.waitIframeIsReady(),
];
const goToMenuItem = [
    clickOnExtraMenuItem({}, true),
    {
        content: "Navigate to model item page",
        trigger: ":iframe a[href='/test_website/model_item/1']",
        run: "click",
    },
    {
        content: "Wait to land on model item page",
        trigger: ':iframe a[href="/test_website/model_item/1"].nav-link.active:not(:visible)',
    },
    stepUtils.waitIframeIsReady(),
];

registerWebsitePreviewTour('test_restricted_editor_only', {
    url: '/',
}, () => [
    // Home
    checkNoTranslate,
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Check icons cannot be dragged",
        trigger: "#snippet_groups .o_snippet[name='Intro'].o_disabled",
        run: function () {
            if (document.querySelector("button.o_snippet_thumbnail_area")) {
                    console.error(
                        "The button to open the add snippet dialog should not be display for restricted editor."
                    );
            }
        },
    },
    ...clickOnSave(),
    ...switchTo('fr'),
    ...translate,
    ...closeErrorDialog,
    ...switchTo('en'),
    // Model item
    {
        trigger: ":iframe body:contains(welcome to your)"
    },
    ...goToMenuItem,
    checkNoTranslate,
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Check icons cannot be dragged",
        trigger: "#snippet_groups .o_snippet[name='Intro'].o_disabled",
        run: function () {
            if (document.querySelector("button.o_snippet_thumbnail_area")) {
                    console.error(
                        "The button to open the add snippet dialog should not be display for restricted editor."
                    );
            }
        },
    },
    ...clickOnSave(),
    ...switchTo('fr'),
    ...translate,
    ...closeErrorDialog,
]);

registerWebsitePreviewTour('test_restricted_editor_test_admin', {
    url: '/',
}, () => [
    // Home
    checkNoTranslate,
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Check icons cannot be dragged",
        trigger: "#snippet_groups .o_snippet[name='Intro'].o_disabled",
    },
    ...clickOnSave(),
    ...switchTo('fr'),
    ...translate,
    ...closeErrorDialog,
    ...switchTo('en'),
    // Model item
    ...goToMenuItem,
    checkNoTranslate,
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Check icons can be dragged",
        trigger: "#snippet_groups .o_snippet[name='Intro']:not(.o_disabled)",
    },
    {
        content: "Drag the Intro snippet group",
        trigger: ".o_block_tab:not(.o_we_ongoing_insertion) #oe_snippets .oe_snippet[name='Intro'] .oe_snippet_thumbnail",
        run: "drag_and_drop :iframe [data-oe-expression='record.website_description']",
    },
    {
        content: "Click on the s_banner snippet in the dialog",
        trigger: ':iframe .o_snippet_preview_wrap[data-snippet-id="s_banner"]',
        run: "click",
    },
    {
        content: "Change name",
        trigger: ":iframe [data-oe-expression='record.name']",
        run: "editor New value",
    },
    ...clickOnSave(),
    ...switchTo('fr'),
    ...translate,
    {
        content: "Close the dialog",
        trigger: ".modal .modal-footer .btn-primary",
        run: "click",
    },
    {
        content: "Assure the modal is well closed",
        trigger: "body:not(:has(.modal))",
    },
    {
        content: "Check that html fields are not content editable when translating",
        trigger: ":iframe [data-oe-expression='record.website_description']:not([contenteditable='true'])",
    },
    {
        content: "Translate name",
        trigger: ":iframe [data-oe-expression='record.name']",
        run: "editor Nouvelle valeur",
    },
    {
        content: "Translate some banner text",
        trigger: ":iframe [data-oe-expression='record.website_description'] strong",
        run: "editor potentiel.",
    },
    ...clickOnSave(),
]);
