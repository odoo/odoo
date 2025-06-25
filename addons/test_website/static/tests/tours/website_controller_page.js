/** @odoo-module **/

import { clickOnSave, registerWebsitePreviewTour } from '@website/js/tours/tour_utils';

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
            const iframeDocument = document.querySelector('.o_website_preview .o_iframe').contentDocument;
            // grid option is selected by default in the switch
            assertEqual(iframeDocument.querySelector(".listing_layout_switcher #o_wstudio_apply_grid").checked, true);
            assertEqual([...iframeDocument.querySelectorAll(".test_record_listing")].length, 2);
        },
    },
    {
        content: "open customize tab",
        trigger: '.o_we_customize_snippet_btn',
        run: "click",
    },
    {
        trigger: "#oe_snippets .o_we_customize_panel",
    },
    {
        content: "open 'Layout' selector",
        trigger: '[data-name="default_listing_layout"] we-toggler',
        run: "click",
    },
    {
        content: "click on 'List' option of the 'Layout' selector",
        trigger: '.o_we_user_value_widget we-button[data-name="list_view_opt"]',
        run: "click",
    },
    {
        content: "records are now displayed in list mode",
        trigger: ':iframe .o_website_list',
        run() {
            const iframeDocument = document.querySelector('.o_website_preview .o_iframe').contentDocument;
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
        trigger: '[is-ready=true]:iframe .o_website_list',
        run() {
            const iframeDocument = document.querySelector('.o_website_preview .o_iframe').contentDocument;
            // list option is selected by default in the switch
            assertEqual(iframeDocument.querySelector(".listing_layout_switcher #o_wstudio_apply_list").checked, true);
            assertEqual([...iframeDocument.querySelectorAll(".test_record_listing")].length, 2);
        },
    },
]);
