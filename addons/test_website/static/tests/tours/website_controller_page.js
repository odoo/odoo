import {
    clickOnSave,
    registerWebsitePreviewTour,
    changeOptionInPopover,
} from "@website/js/tours/tour_utils";

function assertEqual(actual, expected) {
    if (actual !== expected) {
        throw new Error(`Assert failed: expected: ${expected} ; got: ${actual}`);
    }
}

registerWebsitePreviewTour('website_controller_page_listing_layout', {
    url: '/model/exposed-model',
    edition: true,
}, () => [
    {
        content: "website is in preview mode",
        trigger: '.o_website_preview',
        run: "click",
    },
    {
        content: "records are listed in grid mode by default",
        trigger: ':iframe .o_website_grid',
        run() {
            const iframeDocument = document.querySelector(".o_website_preview iframe").contentDocument;
            // grid option is selected by default in the switch
            assertEqual(iframeDocument.querySelector(".listing_layout_switcher #o_wstudio_apply_grid").checked, true);
            assertEqual([...iframeDocument.querySelectorAll(".test_record_listing")].length, 2);
        },
    },
    {
        content: "open customize tab",
        trigger: ":iframe .listing_layout_switcher",
        run: "click",
    },
    {
        trigger: ".o-snippets-menu .o_customize_tab",
    },
    ...changeOptionInPopover("Layout", "Default Layout", "list"),
    {
        content: "records are now displayed in list mode",
        trigger: ':iframe .o_website_list',
        run() {
            const iframeDocument = document.querySelector(".o_website_preview iframe").contentDocument;
            // list option is now selected in the switch
            assertEqual(iframeDocument.querySelector(".listing_layout_switcher #o_wstudio_apply_list").checked, true);
        },
    },
    ...clickOnSave(),
]);

registerWebsitePreviewTour('website_controller_page_default_page_check', {
    url: '/model/exposed-model',
}, () => [
    {
        content: "records are listed in list mode by default",
        trigger: ':iframe [is-ready=true] .o_website_list',
        run() {
            const iframeDocument = document.querySelector(".o_website_preview iframe").contentDocument;
            // list option is selected by default in the switch
            assertEqual(iframeDocument.querySelector(".listing_layout_switcher #o_wstudio_apply_list").checked, true);
            assertEqual([...iframeDocument.querySelectorAll(".test_record_listing")].length, 2);
        },
    },
]);
