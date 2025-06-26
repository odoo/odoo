/** @odoo-module **/

import {
    changeOption,
    clickOnEditAndWaitEditMode,
    clickOnSave,
    clickOnSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';


registerWebsitePreviewTour('website_page_options', {
    url: '/',
    edition: true,
}, () => [
    ...clickOnSnippet({id: 'o_header_standard', name: 'Header'}),
    changeOption('TopMenuVisibility', 'we-select:has([data-visibility]) we-toggler'),
    changeOption('TopMenuVisibility', 'we-button[data-visibility="transparent"]'),
    // It's important to test saving right after changing that option only as
    // this is why this test was made in the first place: the page was not
    // marked as dirty when that option was the only one that was changed.
    ...clickOnSave(),
    {
        content: "Check that the header is transparent",
        trigger: ':iframe #wrapwrap.o_header_overlay',
    },
    ...clickOnEditAndWaitEditMode(),
    ...clickOnSnippet({id: 'o_header_standard', name: 'Header'}),
    changeOption('topMenuColor', 'we-select.o_we_so_color_palette'),
    changeOption('topMenuColor', 'button[data-color="black-50"]', 'background color', 'bottom', true),
    ...clickOnSave(),
    {
        content: "Check that the header is in black-50",
        trigger: ':iframe header#top.bg-black-50',
    },
    ...clickOnEditAndWaitEditMode(),
    ...clickOnSnippet({id: 'o_header_standard', name: 'Header'}),
    changeOption("topMenuColor", '[data-page-option-name="header_text_color"]'),
    changeOption("topMenuColor", 'button[style="background-color:#FF0000;"]', "text color", "bottom", true),
    ...clickOnSave(),
    {
        content: "Check that text color of the header is in red",
        trigger: ':iframe header#top[style=" color: #FF0000;"]',
    },
    {
        content: "Enable the mobile view",
        trigger: ".o_mobile_preview > a",
        run: "click",
    },
    {
        content: "Check that text color of the navbar toggler icon is in red",
        trigger: ':iframe header#top [data-bs-toggle="offcanvas"] .navbar-toggler-icon',
        run: function () {
            if (getComputedStyle(this.anchor).color !== "rgb(255, 0, 0)") {
                console.error("The navbar toggler icon is not in red");
            }
        },
    },
    {
        content: "Disable the mobile view",
        trigger: ".o_mobile_preview > a",
        run: "click",
    },
    ...clickOnEditAndWaitEditMode(),
    ...clickOnSnippet({id: "o_header_standard", name: "Header"}),
    changeOption('TopMenuVisibility', 'we-select:has([data-visibility]) we-toggler'),
    changeOption('TopMenuVisibility', 'we-button[data-visibility="hidden"]'),
    ...clickOnSave(),
    {
        content: "Check that the header is hidden",
        trigger: ':iframe #wrapwrap:has(header#top.d-none.o_snippet_invisible)',
    },
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Click on 'header' in the invisible elements list",
        trigger: '.o_we_invisible_el_panel .o_we_invisible_entry',
        run: "click",
    },
    ...clickOnSnippet({id: 'o_footer', name: 'Footer'}),
    changeOption('HideFooter', 'we-button[data-name="hide_footer_page_opt"] we-checkbox'),
    ...clickOnSave(),
    {
        trigger: ":iframe #wrapwrap header#top:not(.d-none)",
    },
    {
        content: "Check that the footer is hidden and the header is visible",
        trigger: ':iframe #wrapwrap:has(.o_footer.d-none.o_snippet_invisible)',
    },
]);
