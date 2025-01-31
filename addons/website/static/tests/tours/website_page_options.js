import {
    changeOption,
    clickOnEditAndWaitEditMode,
    clickOnSave,
    clickOnSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

const breadcrumb = {id: "o_page_breadcrumb", name: "Breadcrumb"};

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
    changeOption("BaseColorOption", "we-select.o_we_so_color_palette"),
    changeOption(
        "BaseColorOption",
        'button[data-color="black-50"]',
        "background color",
        "bottom",
        true
    ),
    ...clickOnSave(),
    {
        content: "Check that the header is in black-50",
        trigger: ':iframe header#top.bg-black-50',
    },
    ...clickOnEditAndWaitEditMode(),
    ...clickOnSnippet({id: 'o_header_standard', name: 'Header'}),
    changeOption("BaseColorOption", '[data-page-option-name="header_text_color"]'),
    changeOption("BaseColorOption", 'button[style="background-color:#FF0000;"]', "text color", "bottom", true),
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

registerWebsitePreviewTour(
    "website_page_breadcrumb",
    {
        url: "/contactus",
        edition: false,
    },
    () => [
        {
            content: "Check Contact Us page is open",
            trigger: ":iframe html[data-view-xmlid='website.contactus']",
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
            content: "Enable Parent Page Option",
            trigger: "div[name='has_parent_page'] input",
            run: "click",
        },
        {
            content: "Save the changes",
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            content: "Check Breadcrumb is visible",
            trigger: ":iframe div[data-name='Breadcrumb']",
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet(breadcrumb),
        changeOption("WebsiteLevelColor", "we-select.o_we_so_color_palette"),
        {
            content: "Change background color of breadcrumb",
            trigger: "button[data-target='custom-colors']",
            run: "click",
        },
        changeOption(
            "WebsiteLevelColor",
            'button[data-color="black-50"]',
            "background color",
            "bottom",
            true
        ),
        ...clickOnSave(),
        {
            content: "Check that the breadcrumb is in black-50",
            trigger: ":iframe div#wrapwrap main div.o_page_breadcrumb",
            run: function () {
                const rgbString = getComputedStyle(this.anchor)["background-color"];
                return rgbString === "rgba(0, 0, 0, 0.5)";
            },
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet(breadcrumb),
        changeOption("BreadcrumbOptions", "we-select:has([data-visibility]) we-toggler"),
        changeOption("BreadcrumbOptions", 'we-button[data-visibility="transparent"]'),
        ...clickOnSave(),
        {
            content: "Check that the breadcrumb is transparent",
            trigger: ":iframe main.o_breadcrumb_overlay",
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet(breadcrumb),
        changeOption("BaseColorOption", "we-select.o_we_so_color_palette"),
        changeOption(
            "BaseColorOption",
            'button[data-color="black-50"]',
            "background color",
            "bottom",
            true
        ),
        ...clickOnSave(),
        {
            content: "Check that the breadcrumb is in black-50",
            trigger: ":iframe .o_page_breadcrumb.bg-black-50",
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet(breadcrumb),
        changeOption("BreadcrumbOptions", "we-select:has([data-visibility]) we-toggler"),
        changeOption("BreadcrumbOptions", 'we-button[data-visibility="hidden"]'),
        ...clickOnSave(),
        {
            content: "Check that the breadcrumb is hidden",
            trigger: ":iframe main:has(div.o_page_breadcrumb.d-none.o_snippet_invisible)",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Click on 'breacrumb' in the invisible elements list",
            trigger: ".o_we_invisible_el_panel .o_we_invisible_entry",
            run: "click",
        },
    ]
);
