/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

const breadcrumb = {id: "page_breadcrumb", name: "Breadcrumb"};

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
        trigger: ':iframe #wrapwrap.o_header_overlay',
        run: () => null, // it's a check
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.clickOnSnippet({id: 'o_header_standard', name: 'Header'}),
    wTourUtils.changeOption('topMenuColor', 'we-select.o_we_so_color_palette'),
    wTourUtils.changeOption('topMenuColor', 'button[data-color="black-50"]', 'background color', 'bottom', true),
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the header is in black-50",
        trigger: ':iframe header#top.bg-black-50',
        run: () => null, // it's a check
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.clickOnSnippet({id: 'o_header_standard', name: 'Header'}),
    wTourUtils.changeOption('TopMenuVisibility', 'we-select:has([data-visibility]) we-toggler'),
    wTourUtils.changeOption('TopMenuVisibility', 'we-button[data-visibility="hidden"]'),
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the header is hidden",
        trigger: ':iframe #wrapwrap:has(header#top.d-none.o_snippet_invisible)',
        run: () => null, // it's a check
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Click on 'header' in the invisible elements list",
        trigger: '.o_we_invisible_el_panel .o_we_invisible_entry',
        run: "click",
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "Go to Contact Us Page",
        trigger: ":iframe a[href='/contactus']",
        run: "click",
    },
    {
        content: "Check Contact Us page is open",
        trigger: ":iframe html[data-view-xmlid='website.contactus']",
        run : () => null,
    },
    {
        content: "Click on Site Menu",
        trigger: "button[data-menu-xmlid='website.menu_site']",
        run: "click",
    },
    {
        content: "Click on Properties",
        trigger: "a[data-menu-xmlid='website.menu_page_properties']",
        run: "click",
    },
    {
        content: "Click on Publish Page",
        trigger: "a[name='page_publish']",
        run: "click",
    },
    {
        content: "Enable Parent Page Option",
        trigger: "input[id='has_parent_page_0']",
        run: "click",
    },
    {
        content: "Save the changes",
        trigger: "button[data-hotkey='c']",
        run: "click",
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.clickOnSnippet(breadcrumb),
    wTourUtils.changeOption("WebsiteLevelColor", "we-select.o_we_so_color_palette"),
    wTourUtils.changeOption("WebsiteLevelColor", 'button[data-color="black-50"]', "background color", "bottom", true),
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the breadcrumb is in black-50",
        trigger: ":iframe .page_breadcrumb:has(section)",
        run: () => {
            const iframeEl = document.querySelector("iframe");
            const sectionEl = iframeEl.contentDocument.querySelector("main section");
            const rgbString = getComputedStyle(sectionEl)['background-color'];
            return rgbString === 'rgba(0, 0, 0, 0.5)';
        },
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.clickOnSnippet(breadcrumb),
    wTourUtils.changeOption("BreadcrumbOptions", "we-select:has([data-visibility]) we-toggler"),
    wTourUtils.changeOption("BreadcrumbOptions", 'we-button[data-visibility="transparent"]'),
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the header is transparent",
        trigger: ":iframe main.o_breadcrumb_overlay",
        run : () => null,
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.clickOnSnippet(breadcrumb),
    wTourUtils.changeOption("BreadcrumbColor", "we-select.o_we_so_color_palette"),
    wTourUtils.changeOption("BreadcrumbColor", 'button[data-color="black-50"]', "background color", "bottom", true),
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the breadcrumb is in black-50",
        trigger: ":iframe .page_breadcrumb.bg-black-50",
        run : () => null,
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.clickOnSnippet(breadcrumb),
    wTourUtils.changeOption("BreadcrumbOptions", "we-select:has([data-visibility]) we-toggler"),
    wTourUtils.changeOption("BreadcrumbOptions", 'we-button[data-visibility="hidden"]'),
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the breadcrumb is hidden",
        trigger: ":iframe main:has(div.page_breadcrumb.d-none.o_snippet_invisible)",
        run : () => null,
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Click on 'breacrumb' in the invisible elements list",
        trigger: ".o_we_invisible_el_panel .o_we_invisible_entry",
        run: "click",
    },
    wTourUtils.clickOnSnippet({id: 'o_footer', name: 'Footer'}),
    wTourUtils.changeOption('HideFooter', 'we-button[data-name="hide_footer_page_opt"] we-checkbox'),
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the footer is hidden and the header is visible",
        trigger: ':iframe #wrapwrap:has(.o_footer.d-none.o_snippet_invisible)',
        extra_trigger: ':iframe #wrapwrap header#top:not(.d-none)',
        run: () => null, // it's a check
    },
]);
