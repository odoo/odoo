/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("snippet_version", {
    edition: true,
    url: "/",
    test: true,
}, () => [
    wTourUtils.dragNDrop({
        id: 's_test_snip',
        name: 'Test snip',
    }),
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    {
    content: "Test t-snippet and t-snippet-call: snippets have data-snippet set",
    trigger: '#oe_snippets .o_panel_body > .oe_snippet',
    run: function () {
        // Tests done here as all these are not visible on the page
        const draggableSnippets = [...document.querySelectorAll('#oe_snippets .o_panel_body > .oe_snippet:not([data-module-id]) > :nth-child(2)')];
        if (draggableSnippets.length && !draggableSnippets.every(el => el.dataset.snippet)) {
            console.error("error Some t-snippet are missing their template name or there are no snippets to drop");
        }
        if (!document.querySelector('#oe_snippets [data-snippet="s_test_snip"] [data-snippet="s_share"]')) {
            console.error("error s_share t-called inside s_test_snip is missing template name");
        }
        if (!document.querySelector('iframe:not(.o_ignore_in_tour)').contentDocument.querySelector('#wrap [data-snippet="s_test_snip"] [data-snippet="s_share"]')) {
            console.error("error Dropped a s_test_snip snippet but missing s_share template name in it");
        }
    },
},
    ...wTourUtils.clickOnSave(),
    ...wTourUtils.clickOnEditAndWaitEditMode(),
{
    content: "Modify the version of snippets",
    trigger: '#oe_snippets .o_panel_body > .oe_snippet',
    run: function () {
        document.querySelector('#oe_snippets .oe_snippet > [data-snippet="s_test_snip"]').dataset.vjs = '999';
        document.querySelector('#oe_snippets .oe_snippet > [data-snippet="s_share"]').dataset.vcss = '999';
        document.querySelector('#oe_snippets .oe_snippet > [data-snippet="s_text_image"]').dataset.vxml = '999';
    },
}, {
    content: "Edit s_test_snip",
    trigger: 'iframe #wrap.o_editable .s_test_snip',
}, {
    content: "Edit text_image",
    extra_trigger: 'we-customizeblock-options:contains(Test snip) .snippet-option-VersionControl > we-alert',
    trigger: 'iframe #wrap.o_editable .s_text_image',
}, {
    content: "Edit s_share",
    extra_trigger: 'we-customizeblock-options:contains(Text - Image) .snippet-option-VersionControl  > we-alert',
    trigger: 'iframe #wrap.o_editable .s_share',
}, {
    content: "s_share is outdated",
    extra_trigger: 'we-customizeblock-options:contains(Share) .snippet-option-VersionControl > we-alert',
    trigger: 'iframe body',
    isCheck: true,
}]);
