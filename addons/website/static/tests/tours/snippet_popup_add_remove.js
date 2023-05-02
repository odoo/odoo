/** @odoo-module */

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour('snippet_popup_add_remove', {
    test: true,
    url: '/',
    edition: true,
}, [{
    content: 'Drop s_popup snippet',
    trigger: '.oe_snippet:has( > [data-snippet="s_popup"]) .oe_snippet_thumbnail',
    run: "drag_and_drop iframe #wrap",
}, {
    content: 'Edit s_popup snippet',
    in_modal: false,
    trigger: 'iframe #wrap.o_editable [data-snippet="s_popup"] .row > div', // Click deep in the snippet structure
}, {
    content: 'Check s_popup setting are loaded, wait panel is visible',
    in_modal: false,
    trigger: '.o_we_customize_panel',
    run: () => null,
}, {
    content: `Remove the s_popup snippet`,
    in_modal: false,
    trigger: '.o_we_customize_panel we-customizeblock-options:contains("Popup") we-button.oe_snippet_remove:first',
}, {
    content: 'Check the s_popup was removed',
    in_modal: false,
    trigger: 'iframe #wrap.o_editable:not(:has([data-snippet="s_popup"]))',
    run: () => null,
},
// Test that undoing dropping the snippet removes the invisible elements panel.
{
    content: "Drop the snippet again.",
    trigger: '#oe_snippets .oe_snippet:has(> [data-snippet="s_popup"]) .oe_snippet_thumbnail',
    run: "drag_and_drop iframe #wrap",
}, {
    content: "The popup should be in the invisible elements panel.",
    in_modal: false,
    trigger: '.o_we_invisible_el_panel .o_we_invisible_entry',
    run: () => null, // It's a check.
}, {
    content: "Click on the 'undo' button.",
    in_modal: false,
    trigger: '#oe_snippets button[data-action="undo"]',
}, {
    content: "Check that the s_popup was removed.",
    in_modal: false,
    trigger: 'iframe #wrap.o_editable:not(:has([data-snippet="s_popup"]))',
    run: () => null, // It's a check.
}, {
    content: "The invisible elements panel should also be removed.",
    trigger: '#oe_snippets:has(.o_we_invisible_el_panel.d-none)',
    run: () => null, // It's a check.
}]);
