/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';

const snippets = [
    {
        id: 's_text_image',
        name: 'Text - Image',
    },
    {
        id: "s_banner",
        name: "Banner",
    },
    {
        id: "s_popup",
        name: "Popup",
    },
];
function checkEyeIcon(snippetName, visible) {
    const eyeIcon = visible ? "fa-eye" : "fa-eye-slash";
    const openOrClose = visible ? "open" : "close";
    const endExplanation = `should be ${openOrClose} in the "Invisible Elements" panel`;
    const invisibleElPanel = "o_we_invisible_el_panel";
    return {
            content: `The eye icon of ${snippetName} ${endExplanation}`,
            trigger:
            `.${invisibleElPanel} .o_we_invisible_entry:contains("${snippetName}") i.${eyeIcon}`,
            run: () => {}, // it is a check
        };
}
function checkEyesIconAfterSave(footerIsHidden = true) {
    const eyeIconChecks = [
        checkEyeIcon("Header", false),
        checkEyeIcon("Text - Image", true),
        checkEyeIcon("Popup", false),
        checkEyeIcon("Banner", true),
    ];
    if (footerIsHidden) {
        eyeIconChecks.push(checkEyeIcon("Footer", false));
    }
    return eyeIconChecks;
}
wTourUtils.registerWebsitePreviewTour('conditional_visibility_1', {
    edition: true,
    url: '/',
    test: true,
}, () => [
wTourUtils.dragNDrop(snippets[0]),
wTourUtils.clickOnSnippet(snippets[0]),
wTourUtils.changeOption('ConditionalVisibility', 'we-toggler'),
{
    content: 'click on conditional visibility',
    trigger: '[data-name="visibility_conditional"]',
    run: 'click',
},
{
    content: 'click on utm medium toggler',
    trigger: '[data-save-attribute="visibilityValueUtmMedium"] we-toggler',
    run: 'click',
},
{
    trigger: '[data-save-attribute="visibilityValueUtmMedium"] we-selection-items .o_we_m2o_search input',
    content: 'Search for Email',
    run: 'text Email',
},
{
    trigger: '[data-save-attribute="visibilityValueUtmMedium"] we-selection-items [data-add-record="Email"]',
    content: 'click on Email',
    run: 'click',
},
...wTourUtils.clickOnSave(),
{
    content: 'Check if the rule was applied',
    extra_trigger: '.o_website_preview:only-child',
    trigger: 'iframe #wrap',
    allowInvisible: true,
    run: function (actions) {
        const style = window.getComputedStyle(this.$anchor[0].getElementsByClassName('s_text_image')[0]);
        if (style.display !== 'none') {
            console.error('error This item should be invisible and only visible if utm_medium === email');
        }
    },
},
...wTourUtils.clickOnEditAndWaitEditMode(),
{
    content: 'Check if the element is visible as it should always be visible in edit view',
    trigger: 'iframe #wrap .s_text_image',
    run: function (actions) {
        const style = window.getComputedStyle((this.$anchor[0]));
        if (style.display === 'none') {
            console.error('error This item should now be visible because utm_medium === email');
        }
    },
},
]);

wTourUtils.registerWebsitePreviewTour("conditional_visibility_3", {
    edition: true,
    test: true,
    url: "/",
},
() => [
checkEyeIcon("Text - Image", true),
// Drag a "Banner" snippet on the website.
wTourUtils.dragNDrop(snippets[1]),
// Click on the "Banner" snippet.
wTourUtils.clickOnSnippet(snippets[1]),
wTourUtils.changeOption("ConditionalVisibility", "we-toggler"),
wTourUtils.changeOption("ConditionalVisibility", '[data-name="visibility_conditional"]'),
checkEyeIcon("Banner", true),
wTourUtils.goBackToBlocks(),
// Drag a "Popup" snippet on the website.
wTourUtils.dragNDrop(snippets[2]),
{
    content: "Toggle the visibility of the popup",
    in_modal: false,
    trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Popup')",
},
checkEyeIcon("Popup", false),
{
    content: "Click on footer",
    trigger: "iframe #wrapwrap footer",
},
wTourUtils.changeOption("HideFooter", "we-checkbox"),
checkEyeIcon("Footer", false),
{
    content: "Click on Header",
    trigger: "iframe #wrapwrap header",
},
wTourUtils.changeOption("TopMenuVisibility", "we-toggler"),
wTourUtils.changeOption("TopMenuVisibility", '[data-visibility="hidden"]'),
checkEyeIcon("Header", false),
{
    content: "Toggle the visibility of the Banner snippet",
    trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Banner')",
},
checkEyeIcon("Banner", false),
...wTourUtils.clickOnSave(),
...wTourUtils.clickOnEditAndWaitEditMode(),
...checkEyesIconAfterSave(),
]);

wTourUtils.registerWebsitePreviewTour("conditional_visibility_4", {
    edition: true,
    test: true,
    url: "/",
},
() => [
// Click on the "Text-Image" snippet.
wTourUtils.clickOnSnippet(snippets[0]),
{
    content: "Click on the 'move down' option",
    trigger: "iframe we-button.o_we_user_value_widget.fa-angle-down",
},
...checkEyesIconAfterSave(),
{
    content: "Check the order on the 'Invisible Elements' panel",
    trigger: ".o_we_invisible_el_panel div:nth-child(3):contains('Banner')",
    run: () => {}, // it is a check
},
{
    content: "Toggle the visibility of the Footer",
    trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Footer')",
},
{
    content: "Check that the footer is visible",
    trigger: "iframe #wrapwrap footer",
    run: () => {}, // it is a check
},
// Click on the "Banner" snippet.
wTourUtils.clickOnSnippet(snippets[1]),
{
    content: "Drag the 'Banner' snippet to the end of the page",
    trigger: "iframe .o_overlay_move_options .o_move_handle",
    run: "drag_and_drop_native iframe #wrapwrap footer",
},
...checkEyesIconAfterSave(false),
{
    content: "Check the order on the 'Invisible Elements' panel",
    trigger: ".o_we_invisible_el_panel div:nth-child(3):contains('Text - Image')",
    run: () => {}, // it is a check
},
]);
