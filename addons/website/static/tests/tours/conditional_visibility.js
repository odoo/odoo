/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';

const snippets = [
    {
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    },
    {
        id: "s_banner",
        name: "Banner",
        groupName: "Intro",
    },
    {
        id: "s_popup",
        name: "Popup",
        groupName: "Content",
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
...wTourUtils.dragNDrop(snippets[0]),
...wTourUtils.clickOnSnippet(snippets[0]),
wTourUtils.changeOption('ConditionalVisibility', 'we-toggler'),
{
    content: 'click on conditional visibility',
    trigger: '[data-name="visibility_conditional"]',
    run: 'click',
},
{
    content: 'click on utm medium toggler',
    trigger: '[data-attribute-name="visibilityValueUtmMediumRule"] + .o_we_m2m we-toggler',
    run: 'click',
},
{
    trigger: '[data-attribute-name="visibilityValueUtmMediumRule"] + .o_we_m2m we-selection-items .o_we_m2o_search input',
    content: 'Search for Email',
    run: "edit Email",
},
{
    trigger: '[data-attribute-name="visibilityValueUtmMediumRule"] + .o_we_m2m we-selection-items [data-add-record="Email"]',
    content: 'click on Email',
    run: 'click',
},
...wTourUtils.clickOnSave(),
{
    trigger: ".o_website_preview:only-child",
},
{
    content: 'Check if the rule was applied',
    trigger: ':iframe #wrap:not(:visible)',
    run: function (actions) {
        const style = window.getComputedStyle(this.anchor.getElementsByClassName('s_text_image')[0]);
        if (style.display !== 'none') {
            console.error('error This item should be invisible and only visible if utm_medium === email');
        }
    },
},
...wTourUtils.clickOnEditAndWaitEditMode(),
{
    content: 'Check if the element is visible as it should always be visible in edit view',
    trigger: ':iframe #wrap .s_text_image',
    run: function (actions) {
        const style = window.getComputedStyle((this.anchor));
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
...wTourUtils.dragNDrop(snippets[1]),
// Click on the "Banner" snippet.
...wTourUtils.clickOnSnippet(snippets[1]),
wTourUtils.changeOption("ConditionalVisibility", "we-toggler"),
wTourUtils.changeOption("ConditionalVisibility", '[data-name="visibility_conditional"]'),
checkEyeIcon("Banner", true),
wTourUtils.goBackToBlocks(),
// Drag a "Popup" snippet on the website.
...wTourUtils.dragNDrop(snippets[2]),
{
    content: "Toggle the visibility of the popup",
    trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Popup')",
    run: "click",
},
checkEyeIcon("Popup", false),
{
    content: "Click on footer",
    trigger: ":iframe #wrapwrap footer",
    run: "click",
},
wTourUtils.changeOption("HideFooter", "we-checkbox"),
checkEyeIcon("Footer", false),
{
    content: "Click on Header",
    trigger: ":iframe #wrapwrap header",
    run: "click",
},
wTourUtils.changeOption("TopMenuVisibility", "we-toggler"),
wTourUtils.changeOption("TopMenuVisibility", '[data-visibility="hidden"]'),
checkEyeIcon("Header", false),
{
    content: "Toggle the visibility of the Banner snippet",
    trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Banner')",
    run: "click",
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
...wTourUtils.clickOnSnippet(snippets[0]),
{
    content: "Click on the 'move down' option",
    trigger: ":iframe we-button.o_we_user_value_widget.fa-angle-down",
    run: "click",
},
...checkEyesIconAfterSave(),
{
    content: "Check the order on the 'Invisible Elements' panel",
    trigger: ".o_we_invisible_el_panel div:nth-child(3):contains('Banner')",
},
{
    content: "Toggle the visibility of the Footer",
    trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Footer')",
    run: "click",
},
{
    content: "Check that the footer is visible",
    trigger: ":iframe #wrapwrap footer",
},
// Click on the "Banner" snippet.
...wTourUtils.clickOnSnippet(snippets[1]),
{
    content: "Drag the 'Banner' snippet to the end of the page",
    trigger: ":iframe .o_overlay_move_options .o_move_handle",
    run: "drag_and_drop :iframe #wrapwrap footer",
},
...checkEyesIconAfterSave(false),
{
    content: "Check the order on the 'Invisible Elements' panel",
    trigger: ".o_we_invisible_el_panel div:nth-child(3):contains('Text - Image')",
},
]);

wTourUtils.registerWebsitePreviewTour("conditional_visibility_5", {
    edition: true,
    test: true,
    url: "/",
}, () => [
    {
        content: "Toggle the visibility of the Footer",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Footer')",
        run: "click",
    },
    {
        content: "Check that the footer is visible",
        trigger: ":iframe #wrapwrap footer",
    },
    ...wTourUtils.dragNDrop(snippets[0]),
    {
        content: "Click on the image of the dragged snippet",
        trigger: ":iframe .s_text_image img",
        run: "click",
    },
    wTourUtils.changeOption("DeviceVisibility", 'we-button[data-toggle-device-visibility="no_desktop"]'),
    {
        content: "Check that the Column has been added in the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Column')",
    },
    {
        content: "Click on the 'Text - Image' snippet",
        trigger: ":iframe .s_text_image",
        run: "click",
    },
    wTourUtils.changeOption("ConditionalVisibility", 'we-button[data-toggle-device-visibility="no_desktop"]'),
    {
        content: "Check that the 'Text - Image' is the parent of 'Column' in the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_root_parent.o_we_invisible_entry:contains('Text - Image') + ul .o_we_invisible_entry.o_we_sublevel_1:contains('Column')",
    },
    {
        content: "Click on the 'Text - Image' entry on the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_root_parent.o_we_invisible_entry:contains('Text - Image')",
        run: "click",
    },
    {
        content: "Check that the snippet is visible on the website",
        trigger: ":iframe .s_text_image.o_snippet_desktop_invisible.o_snippet_override_invisible",
    },
    wTourUtils.changeOption("ConditionalVisibility", 'we-button[data-toggle-device-visibility="no_mobile"]'),
    {
        content: "Check that the 'Text - Image' has been removed from the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel:not(.o_we_invisible_entry:contains('Text - Image'))",
    },
    {
        content: "Click on the 'Column' entry on the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Column')",
        run: "click",
    },
    {
        content: "Check that the column is visible on the website",
        trigger: ":iframe .s_text_image .row > .o_snippet_desktop_invisible.o_snippet_override_invisible",
    },
    wTourUtils.changeOption("DeviceVisibility", 'we-button[data-toggle-device-visibility="no_mobile"]'),
    {
        content: "Check that the column has been removed from the 'Invisible Elements' panel",
        trigger: "#oe_snippets:not(:has(.o_we_invisible_entry:contains('Column')))",
    },
    {
        content: "Activate mobile preview",
        trigger: ".o_we_website_top_actions button[data-action='mobile']",
        run: "click",
    },
    {
        content: "Check that the 'Text - Image' is the parent of 'Column' in the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_root_parent.o_we_invisible_entry:contains('Text - Image') + ul .o_we_invisible_entry.o_we_sublevel_1:contains('Column')",
    },
]);
