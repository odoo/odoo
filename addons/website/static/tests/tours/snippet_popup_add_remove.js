/** @odoo-module */

import tour from 'web_tour.tour';

tour.register('snippet_popup_add_remove', {
    test: true,
    url: '/?enable_editor=1',
}, [{
    content: 'Drop s_popup snippet',
    trigger: '#oe_snippets .oe_snippet:has( > [data-snippet="s_popup"]) .oe_snippet_thumbnail',
    run: "drag_and_drop #wrap",
}, {
    content: 'Edit s_popup snippet',
    in_modal: false,
    trigger: '#wrap.o_editable [data-snippet="s_popup"] .row > div', // Click deep in the snippet structure
}, {
    content: 'Check s_popup setting are loaded, wait panel is visible',
    in_modal: false,
    trigger: '.o_we_customize_panel',
    run: () => null,
}, {
    content: `Remove the s_popup snippet`,
    in_modal: false,
    trigger: '.o_we_customize_panel we-button.oe_snippet_remove:first',
}, {
    content: 'Check the s_popup was removed',
    in_modal: false,
    trigger: '#wrap.o_editable:not(:has([data-snippet="s_popup"]))',
    run: () => null,
}]);
