/** @odoo-module */

import {
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('snippet_popup_add_remove', {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({
        name: "Popup",
        id: "s_popup",
        groupName: "Content",
}), {
    content: 'Edit s_popup snippet',
    trigger: ':iframe #wrap.o_editable [data-snippet="s_popup"] .row > div', // Click deep in the snippet structure
    run: "click",
}, {
    content: 'Check s_popup setting are loaded, wait panel is visible',
    trigger: '.o_we_customize_panel',
}, {
    content: `Remove the s_popup snippet`,
    trigger: '.o_we_customize_panel we-customizeblock-options:contains("Popup") we-button.oe_snippet_remove:first',
    run: "click",
}, {
    content: 'Check the s_popup was removed',
    trigger: ':iframe #wrap.o_editable:not(:has([data-snippet="s_popup"]))',
},
// Test that undoing dropping the snippet removes the invisible elements panel.
...insertSnippet({
    name: "Popup",
    id: "s_popup",
    groupName: "Content",
}), {
    content: "The popup should be in the invisible elements panel.",
    trigger: '.o_we_invisible_el_panel .o_we_invisible_entry',
}, {
    content: "Click on the 'undo' button.",
    trigger: '#oe_snippets button.fa-undo',
    run: "click",
}, {
    content: "Check that the s_popup was removed.",
    trigger: ':iframe #wrap.o_editable:not(:has([data-snippet="s_popup"]))',
}, {
    content: "The invisible elements panel should also be removed.",
    trigger: '#oe_snippets:not(:has(.o_we_invisible_el_panel)',
}]);
