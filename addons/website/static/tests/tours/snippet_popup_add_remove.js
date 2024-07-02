/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour('snippet_popup_add_remove', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    ...wTourUtils.dragNDrop({
        name: "Popup",
        id: "s_popup"
}), {
    content: 'Edit s_popup snippet',
    in_modal: false,
    trigger: ':iframe #wrap.o_editable [data-snippet="s_popup"] .row > div', // Click deep in the snippet structure
    run: "click",
}, {
    content: 'Check s_popup setting are loaded, wait panel is visible',
    in_modal: false,
    trigger: '.o_we_customize_panel',
}, {
    content: `Remove the s_popup snippet`,
    in_modal: false,
    trigger: '.o_we_customize_panel we-customizeblock-options:contains("Popup") we-button.oe_snippet_remove:first',
    run: "click",
}, {
    content: 'Check the s_popup was removed',
    in_modal: false,
    trigger: ':iframe #wrap.o_editable:not(:has([data-snippet="s_popup"]))',
},
// Test that undoing dropping the snippet removes the invisible elements panel.
...wTourUtils.dragNDrop({
    name: "Popup",
    id: "s_popup"
}), {
    content: "The popup should be in the invisible elements panel.",
    in_modal: false,
    trigger: '.o_we_invisible_el_panel .o_we_invisible_entry',
}, {
    content: "Click on the 'undo' button.",
    in_modal: false,
    trigger: '#oe_snippets button.fa-undo',
    run: "click",
}, {
    content: "Check that the s_popup was removed.",
    in_modal: false,
    trigger: ':iframe #wrap.o_editable:not(:has([data-snippet="s_popup"]))',
}, {
    content: "The invisible elements panel should also be removed.",
    trigger: '#oe_snippets:not(:has(.o_we_invisible_el_panel)',
}]);
