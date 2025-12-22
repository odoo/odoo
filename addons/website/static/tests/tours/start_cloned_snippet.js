/** @odoo-module **/

import {
    clickOnSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('website_start_cloned_snippet', {
    edition: true,
    url: '/',
}, () => {
    const countdownSnippet = {
        name: 'Countdown',
        id: 's_countdown',
    };
    return [
        {
            trigger: ".o_website_preview.editor_enable.editor_has_snippets",
        },
        {
            trigger: `#oe_snippets .oe_snippet[name="${countdownSnippet.name}"].o_we_draggable .oe_snippet_thumbnail:not(.o_we_ongoing_insertion)`,
            run: "drag_and_drop :iframe #wrapwrap #wrap",
        },
        ...clickOnSnippet(countdownSnippet),
        {
            content: 'Click on clone snippet',
            trigger: '.oe_snippet_clone',
            run: "click",
        },
        {
            content: 'Check that the cloned snippet has a canvas and that something has been drawn inside of it',
            trigger: ':iframe .s_countdown:eq(1) canvas',
            run: function () {
                // Check that at least one bit has been drawn in the canvas
                if (!this.anchor.getContext("2d").getImageData(0, 0, 1000, 1000).data.includes(1)) {
                    console.error('The cloned snippet should have been started');
                }
            },
        },

    ]
});
