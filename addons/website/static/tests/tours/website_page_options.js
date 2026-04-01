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
