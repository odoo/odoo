/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour('website_page_options', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    wTourUtils.clickOnSnippet({id: 'o_header_standard', name: 'Header'}),
    wTourUtils.changeOption('TopMenuVisibility', 'we-select:has([data-visibility]) we-toggler'),
    wTourUtils.changeOption('TopMenuVisibility', 'we-button[data-visibility="transparent"]'),
    // It's important to test saving right after changing that option only as
    // this is why this test was made in the first place: the page was not
    // marked as dirty when that option was the only one that was changed.
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the header is transparent",
        trigger: 'iframe #wrapwrap.o_header_overlay',
        run: () => null, // it's a check
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.clickOnSnippet({id: 'o_header_standard', name: 'Header'}),
    wTourUtils.changeOption('topMenuColor', 'we-select.o_we_so_color_palette'),
    wTourUtils.changeOption('topMenuColor', 'button[data-color="black-50"]', 'background color', 'bottom', true),
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the header is in black-50",
        trigger: 'iframe header#top.bg-black-50',
        run: () => null, // it's a check
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.clickOnSnippet({id: 'o_header_standard', name: 'Header'}),
    wTourUtils.changeOption('TopMenuVisibility', 'we-select:has([data-visibility]) we-toggler'),
    wTourUtils.changeOption('TopMenuVisibility', 'we-button[data-visibility="hidden"]'),
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the header is hidden",
        trigger: 'iframe #wrapwrap:has(header#top.d-none.o_snippet_invisible)',
        run: () => null, // it's a check
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Click on 'header' in the invisible elements list",
        trigger: '.o_we_invisible_el_panel .o_we_invisible_entry',
    },
    wTourUtils.clickOnSnippet({id: 'o_footer', name: 'Footer'}),
    wTourUtils.changeOption('HideFooter', 'we-button[data-name="hide_footer_page_opt"] we-checkbox'),
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the footer is hidden and the header is visible",
        trigger: 'iframe #wrapwrap:has(.o_footer.d-none.o_snippet_invisible)',
        extra_trigger: 'iframe #wrapwrap header#top:not(.d-none)',
        run: () => null, // it's a check
    },
]);
