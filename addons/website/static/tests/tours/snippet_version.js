odoo.define("website.tour.snippet_version", function (require) {
"use strict";

var tour = require("web_tour.tour");

tour.register("snippet_version", {
    test: true,
    url: "/",
}, [{
    content: "Enter edit mode",
    trigger: 'a[data-action=edit]',
}, {
    content: "Drop s_test_snip snippet",
    trigger: '#oe_snippets .oe_snippet:has(.s_test_snip) .oe_snippet_thumbnail',
    run: async (action_helper) => {
        action_helper.drag_and_drop('#wrap');
        // wait the last operation of the editor before saving.
        $('#wrap').addClass('action-loading');
        await new Promise(r => setTimeout(r, 0));
        await new Promise(r => setTimeout(r, 0));
        $('#wrap').removeClass('action-loading');
    },
}, {
    content: "Drop s_text_image snippet",
    extra_trigger: '#wrap:not(.action-loading)',
    trigger: '#oe_snippets .oe_snippet:has(.s_text_image) .oe_snippet_thumbnail:not(.o_we_already_dragging)',
    run: async (action_helper) => {
        action_helper.drag_and_drop('#wrap');
        // wait the last operation of the editor before saving.
        $('#wrap').addClass('action-loading');
        await new Promise(r => setTimeout(r, 0));
        await new Promise(r => setTimeout(r, 0));
        $('#wrap').removeClass('action-loading');
    },
}, {
    content: "Test t-snippet and t-snippet-call: snippets have data-snippet set",
    extra_trigger: '#wrap:not(.action-loading)',
    trigger: '#oe_snippets .o_panel_body > .oe_snippet.ui-draggable',
    run: function () {
        // Tests done here as all these are not visible on the page
        const draggableSnippets = document.querySelectorAll('#oe_snippets .o_panel_body > .oe_snippet.ui-draggable > :nth-child(2)');
        if (![...draggableSnippets].every(el => el.dataset.snippet)) {
            console.error("error Some t-snippet are missing their template name");
        }
        if (!document.querySelector('#oe_snippets [data-snippet="s_test_snip"] [data-snippet="s_share"]')) {
            console.error("error s_share t-called inside s_test_snip is missing template name");
        }
        if (!document.querySelector('#wrap [data-snippet="s_test_snip"] [data-snippet="s_share"]')) {
            console.error("error Dropped a s_test_snip snippet but missing s_share template name in it");
        }
    },
}, {
    content: "Enter edit mode",
    trigger: 'button[name="save"]',
}, {
    content: "Enter edit mode",
    extra_trigger: 'body:not(.editor_enable)',
    trigger: 'a[data-action=edit]',
}, {
    content: "Modify the version of snippets",
    trigger: '#oe_snippets .o_panel_body > .oe_snippet',
    run: function () {
        document.querySelector('#oe_snippets .oe_snippet > [data-snippet="s_test_snip"]').dataset.vjs = '999';
        document.querySelector('#oe_snippets .oe_snippet > [data-snippet="s_share"]').dataset.vcss = '999';
        document.querySelector('#oe_snippets .oe_snippet > [data-snippet="s_text_image"]').dataset.vxml = '999';
    },
}, {
    content: "Edit s_test_snip",
    trigger: '#wrap.o_editable .s_test_snip',
}, {
    content: "Edit text_image",
    extra_trigger: 'we-customizeblock-options:contains(Test snip) .snippet-option-VersionControl > we-alert',
    trigger: '#wrap.o_editable .s_text_image',
}, {
    content: "Edit s_share",
    extra_trigger: 'we-customizeblock-options:contains(Text - Image) .snippet-option-VersionControl  > we-alert',
    trigger: '#wrap.o_editable .s_share',
    run: async function (actions) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        actions.auto();
    },
}, {
    content: "s_share is outdated",
    extra_trigger: 'we-customizeblock-options:contains(Share) .snippet-option-VersionControl > we-alert',
    trigger: 'body',
}]);
});
