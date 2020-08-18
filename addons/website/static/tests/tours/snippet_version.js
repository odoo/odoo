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
    content: "Drop s_carousel snippet",
    trigger: '#oe_snippets .oe_snippet:has(.s_carousel) .oe_snippet_thumbnail',
    run: "drag_and_drop #wrap",
}, {
    content: "Drop s_carousel snippet",
    trigger: '#oe_snippets .oe_snippet:has(.s_text_image) .oe_snippet_thumbnail',
    run: "drag_and_drop #wrap",
}, {
    content: "Test t-snippet and t-snippet-call: snippets have data-snippet set",
    trigger: '#oe_snippets .o_panel_body > .oe_snippet.ui-draggable',
    run: function () {
        // Tests done here as all these are not visible on the page
        const draggableSnippets = document.querySelectorAll('#oe_snippets .o_panel_body > .oe_snippet.ui-draggable > :nth-child(2)');
        if (![...draggableSnippets].every(el => el.dataset.snippet)) {
            console.error("error Some t-snippet are missing their template name");
        }
        // Currently only s_share is t-snippet-call, if it's removed find a way to keep t-snippet-call tested !!.
        if (!document.querySelector('#oe_snippets [data-snippet="s_carousel"] [data-snippet="s_share"]')) {
            console.error("error s_share t-called inside s_carousel is missing template name");
        }
        if (!document.querySelector('#wrap [data-snippet="s_carousel"] [data-snippet="s_share"]')) {
            console.error("error Dropped a s_carousel snippet but missing s_share template name in it");
        }
    },
}, {
    content: "Enter edit mode",
    trigger: 'button[data-action="save"]',
}, {
    content: "Enter edit mode",
    extra_trigger: 'body:not(.editor_enable)',
    trigger: 'a[data-action=edit]',
}, {
    content: "Modify the version of snippets",
    trigger: '#oe_snippets .o_panel_body > .oe_snippet',
    run: function () {
        document.querySelector('#oe_snippets .oe_snippet > [data-snippet="s_carousel"]').dataset.vjs = '999';
        document.querySelector('#oe_snippets .oe_snippet > [data-snippet="s_share"]').dataset.vcss = '999';
        document.querySelector('#oe_snippets .oe_snippet > [data-snippet="s_text_image"]').dataset.vxml = '999';
    },
}, {
    content: "Edit carousel",
    trigger: '#wrap.o_editable .s_carousel',
}, {
    content: "Edit text_image",
    extra_trigger: 'we-customizeblock-options:contains(Carousel) .snippet-option-VersionControl > we-alert',
    trigger: '#wrap.o_editable .s_text_image',
}, {
    content: "Got to s_share slide",
    extra_trigger: 'we-customizeblock-options:contains(Text - Image) .snippet-option-VersionControl  > we-alert',
    trigger: '#wrap.o_editable .s_carousel .carousel-control-prev',
    run: function () {
        $('#wrap.o_editable .s_carousel').carousel(2);
    },
}, {
    content: "Edit s_share",
    trigger: '#wrap.o_editable .s_share',
}, {
    content: "s_share is outdated",
    extra_trigger: 'we-customizeblock-options:contains(Share) .snippet-option-VersionControl > we-alert',
    trigger: 'body',
}]);
});
