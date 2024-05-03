import {
    changeOptionInPopover,
    clickOnEditAndWaitEditMode,
    clickOnSave,
    clickOnSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_page_options",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...clickOnSnippet({ id: "o_header_standard", name: "Header" }),
        ...changeOptionInPopover("Header", "Header Position", "Over the content"),
        // It's important to test saving right after changing that option only as
        // this is why this test was made in the first place: the page was not
        // marked as dirty when that option was the only one that was changed.
        ...clickOnSave(),
        {
            content: "Check that the header is transparent",
            trigger: ":iframe #wrapwrap.o_header_overlay",
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet({ id: "o_header_standard", name: "Header" }),
        {
            content: "Open the color picker to change the background color of the header",
            trigger:
                "div[data-container-title='Header'] .hb-row[data-label='Header Position'] + .hb-row-sublevel-1[data-label='Background'] button",
            run: "click",
        },
        {
            content: "Select the color black-600",
            trigger: ".popover button[data-color='600']",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Check that the header is in black-600",
            trigger: ":iframe header#top.bg-600",
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet({ id: "o_header_standard", name: "Header" }),
        {
            content: "Open the color picker to change the text color of the header",
            trigger:
                "div[data-container-title='Header'] .hb-row-sublevel-1[data-label='Text Color'] button",
            run: "click",
        },
        {
            content: "Select the color red",
            trigger: ".popover button[data-color='#FF0000']",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Check that text color of the header is in red",
            trigger: ':iframe header#top[style=" color: #ff0000;"]',
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
        ...clickOnSnippet({ id: "o_header_standard", name: "Header" }),
        ...changeOptionInPopover("Header", "Header Position", "Hidden"),
        ...clickOnSave(),
        {
            content: "Check that the header is hidden",
            trigger: ":iframe #wrapwrap:has(header#top.d-none.o_snippet_invisible)",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Click on 'header' in the invisible elements list",
            trigger: ".o_we_invisible_el_panel .o_we_invisible_entry",
            run: "click",
        },
        ...clickOnSnippet({ id: "o_footer", name: "Footer" }),
        {
            content: "Click on the visibility toggle to change the visibility of the footer",
            trigger:
                "div[data-container-title='Footer'] div[data-label='Page Visibility'] div[data-action-id='setWebsiteFooterVisible'] input",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Check that the header is visible",
            trigger: ":iframe #wrapwrap header#top:not(.d-none)",
        },
        {
            content: "Check that the footer is hidden",
            trigger: ":iframe #wrapwrap:has(.o_footer.d-none.o_snippet_invisible)",
        },
    ]
);

const breadcrumb = { id: "o_page_breadcrumb", name: "Breadcrumb" };
let selectedGradient = null;

function openColorPicker(type) {
    return [
        {
            content: "Open the color picker for breadcrumb",
            trigger: `div[data-label='${type}'] .o_we_color_preview`,
            run: "click",
        },
    ];
}

function openBackgroundColorPicker(type, selector) {
    return [
        ...openColorPicker(type),
        {
            content: `Open ${selector} tab`,
            trigger: `.o_font_color_selector button:contains(${selector})`,
            run: "click",
        },
    ];
}

registerWebsitePreviewTour(
    "website_page_breadcrumb",
    {
        url: "/contactus",
        edition: false,
    },
    () => [
        {
            content: "Open the Site Menu",
            trigger: "button[data-menu-xmlid='website.menu_site']",
            run: "click",
        },
        {
            content: "Select the Properties option from the menu",
            trigger: "a[data-menu-xmlid='website.menu_page_properties']",
            run: "click",
        },
        {
            content: "Enable the Parent Page Option",
            trigger: "div[name='has_parent_page'] input",
            run: "click",
        },
        {
            content: "Save the changes",
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            content: "Verify that the Breadcrumb is visible",
            trigger: ":iframe div[data-name='Breadcrumb']",
        },
        {
            content: "Verify that Home is displayed in the breadcrumb",
            trigger:
                ":iframe nav[aria-label='breadcrumb'] ol.breadcrumb li:first-child a:contains(Home)",
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet(breadcrumb),
        ...openBackgroundColorPicker("Background Color", "Theme"),
        {
            content: "Apply Preset-4 background color to the breadcrumb",
            trigger: ".o_cc_preview_wrapper button[data-color='o_cc4']",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Verify that the breadcrumb background color matches Preset 4",
            trigger: ":iframe nav[aria-label='breadcrumb']",
            run() {
                const occBg = getComputedStyle(document.documentElement)
                    .getPropertyValue("--o-cc4-bg")
                    .trim();
                const breadcrumbBgPreset = getComputedStyle(this.anchor)
                    .getPropertyValue("--o-cc-bg")
                    .trim();
                if (occBg != breadcrumbBgPreset) {
                    console.error(
                        `Expected Preset 4 background but received "${breadcrumbBgPreset}"`
                    );
                }
            },
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet(breadcrumb),
        ...openBackgroundColorPicker("Background Color", "Custom"),
        {
            content: "Set the breadcrumb background color to black-600",
            trigger: ".popover button[data-color='600']",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Verify that the breadcrumb background color is black-600",
            trigger: ":iframe .o_page_breadcrumb nav",
            run() {
                const bgColor = getComputedStyle(this.anchor).backgroundColor;
                if (bgColor !== "rgb(108, 117, 125)") {
                    console.error(
                        `Expected breadcrumb background rgb(108,117,125) but received ${bgColor}`
                    );
                }
            },
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet(breadcrumb),
        ...openBackgroundColorPicker("Background Color", "Gradient"),
        {
            content: "Apply the first gradient option to the breadcrumb background",
            trigger: ".o_colorpicker_sections button.o_gradient_color_button",
            run() {
                selectedGradient = this.anchor.dataset.color;
                this.anchor.click();
            },
        },
        {
            content: "Verify that the breadcrumb background gradient is applied correctly",
            trigger: ":iframe nav[aria-label='breadcrumb']",
            run() {
                const breadcrumbBgGradient = getComputedStyle(this.anchor).backgroundImage.trim();
                if (breadcrumbBgGradient !== selectedGradient) {
                    console.error(
                        `Expected breadcrumb background gradient "${selectedGradient}" but received "${breadcrumbBgGradient}"`
                    );
                }
            },
        },
        ...changeOptionInPopover("Breadcrumb", "Breadcrumb Position", "Over the content"),
        ...clickOnSave(),
        {
            content: "Verify that the breadcrumb is positioned over the content",
            trigger: ":iframe main.o_breadcrumb_overlay",
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet(breadcrumb),
        ...openColorPicker("Background"),
        {
            content: "Set the breadcrumb background color to black-600",
            trigger: ".popover button[data-color='600']",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Verify that the breadcrumb background color is black-600",
            trigger: ":iframe .o_page_breadcrumb.bg-600",
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet(breadcrumb),
        ...openColorPicker("Text Color"),
        {
            content: "Set the breadcrumb text color to red",
            trigger: ".popover button[data-color='#FF0000']",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Verify that the breadcrumb text color is red",
            trigger: ':iframe .o_page_breadcrumb[style*="color: rgb(255, 0, 0)"]',
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet(breadcrumb),
        ...changeOptionInPopover("Breadcrumb", "Breadcrumb Position", "Hidden"),
        ...clickOnSave(),
        {
            content: "Verify that the breadcrumb is hidden",
            trigger: ":iframe main:has(div.o_page_breadcrumb.d-none.o_snippet_invisible)",
        },
    ]
);
