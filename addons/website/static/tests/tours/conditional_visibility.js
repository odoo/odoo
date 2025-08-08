import {
    changeOptionInPopover,
    clickOnEditAndWaitEditMode,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    goBackToBlocks,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

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
    {
        id: 's_image_text',
        name: 'Image - Text',
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
registerWebsitePreviewTour('conditional_visibility_1', {
    edition: true,
    url: '/',
}, () => [
...insertSnippet(snippets[0]),
...clickOnSnippet(snippets[0]),
...changeOptionInPopover("Text - Image", "Visibility", "Conditionally"),
{
    content: 'click on utm medium toggler',
    trigger: '[data-label="UTM Medium"] ~ div button.dropdown-toggle:contains("Choose a record...")',
    run: 'click',
},
{
    trigger: '.o_popover input',
    content: 'Search for Email',
    run: "edit Email",
},
{
    trigger: ".o_popover .o-dropdown-item:contains('Email')",
    content: 'click on Email',
    run: 'click',
},
...clickOnSave(),
{
    trigger: ".o_website_preview",
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
...clickOnEditAndWaitEditMode(),
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

registerWebsitePreviewTour("conditional_visibility_3", {
    edition: true,
    url: "/",
},
() => [
checkEyeIcon("Text - Image", true),
// Drag a "Banner" snippet on the website.
...insertSnippet(snippets[1]),
// Click on the "Banner" snippet.
...clickOnSnippet(snippets[1]),
...changeOptionInPopover("Banner", "Visibility", "Conditionally"),
checkEyeIcon("Banner", true),
goBackToBlocks(),
// Drag a "Popup" snippet on the website.
...insertSnippet(snippets[2]),
{
    content: "Wait for the popup to display",
    trigger: ":iframe .s_popup .modal_shown",
},
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
{
    content: "Click on Page Visibility",
    trigger: "[data-container-title='Footer'] [data-label='Page Visibility'] [data-action-id='setWebsiteFooterVisible'] .form-check-input",
    run: "click",
},
checkEyeIcon("Footer", false),
{
    content: "Click on Header",
    trigger: ":iframe #wrapwrap header",
    run: "click",
},
...changeOptionInPopover("Header", "Header Position", "[data-action-value='hidden']"),
checkEyeIcon("Header", false),
...clickOnSnippet(snippets[1]),
...changeOptionInPopover("Banner", "Visibility", "Conditionally"),
{
    content: "Toggle the visibility of the Banner",
    trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Banner')",
    run: "click",
},
checkEyeIcon("Banner", false),
...clickOnSave(),
...clickOnEditAndWaitEditMode(),
...checkEyesIconAfterSave(),
]);

registerWebsitePreviewTour("conditional_visibility_4", {
    edition: true,
    url: "/",
},
() => [
// Click on the "Text-Image" snippet.
...clickOnSnippet(snippets[0]),
{
    content: "Click on the 'move down' option",
    trigger: ".o_overlay_options button.fa-angle-down",
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
...clickOnSnippet(snippets[1]),
{
    content: "Drag the 'Banner' snippet to the end of the page",
    trigger: ".o_overlay_options button.o_move_handle",
    run: "drag_and_drop :iframe #wrapwrap footer",
},
...checkEyesIconAfterSave(false),
{
    content: "Check the order on the 'Invisible Elements' panel",
    trigger: ".o_we_invisible_el_panel div:nth-child(3):contains('Text - Image')",
},
]);

registerWebsitePreviewTour("conditional_visibility_5", {
    edition: true,
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
    goBackToBlocks(),
    ...insertSnippet(snippets[3]),
    {
        content: "Click on the image of the dragged snippet",
        trigger: ":iframe .s_text_image[data-snippet=s_image_text] img",
        run: "click",
    },
    {
        content: "Change visibility of the 'Image - Text' snippet",
        trigger: "[data-container-title='Column'] [data-label='Visibility'] button[data-action-param='no_desktop']",
        run: "click",
    },
    {
        content: "Check that the Column has been added in the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Column')",
    },
    {
        content: "Click on the 'Image - Text' snippet",
        trigger: ":iframe .s_text_image[data-snippet=s_image_text]",
        run: "click",
    },
    {
        content: "Change visibility of the 'Image - Text' snippet",
        trigger: "[data-container-title='Image - Text'] [data-label='Visibility'] button[data-action-param='no_desktop']",
        run: "click",
    },
    {
        content: "Check that only the 'Image - Text' entry is in the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_root_parent.o_we_invisible_entry:contains('Image - Text') + .o_we_invisible_entry:not(.o_we_sublevel_1)",
    },
    {
        content: "Click on the 'Image - Text' entry on the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_root_parent.o_we_invisible_entry:contains('Image - Text')",
        run: "click",
    },
    {
        content: "Check that the snippet is visible on the website",
        trigger: ":iframe .s_text_image[data-snippet=s_image_text].o_snippet_desktop_invisible.o_snippet_override_invisible",
    },
    {
        content: "Check that the 'Column' entry is in the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel ul .o_we_invisible_entry.o_we_sublevel_1:contains('Column')",
    },
    {
        content: "Change visibility of the 'Image - Text' snippet",
        trigger: "[data-container-title='Image - Text'] [data-label='Visibility'] button[data-action-param='no_mobile']",
        run: "click",
    },
    {
        content: "Check that the 'Image - Text' has been removed from the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel:not(:has(.o_we_invisible_entry:contains('Image - Text')))",
    },
    {
        content: "Click on the 'Column' entry on the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Column')",
        run: "click",
    },
    {
        content: "Check that the column is visible on the website",
        trigger: ":iframe .s_text_image[data-snippet=s_image_text] .row > .o_snippet_desktop_invisible.o_snippet_override_invisible",
    },
    {
        content: "Change visibility of the 'Image - Text' snippet",
        trigger: "[data-container-title='Column'] [data-label='Visibility'] button[data-action-param='no_mobile']",
        run: "click",
    },
    {
        content: "Check that the column has been removed from the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel:not(:has(.o_we_invisible_entry:contains('Column')))",
    },
    {
        content: "Check that the 'Image - Text' entry has been removed from the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel:not(:has(.o_we_invisible_entry:contains('Image - Text')))",
    },
    {
        content: "Activate mobile preview",
        trigger: ".o-snippets-top-actions button[data-action='mobile']",
        run: "click",
    },
    {
        content: "Check that the 'Image - Text' entry is in the 'Invisible Elements' panel",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry:contains('Image - Text')",
    },
]);
