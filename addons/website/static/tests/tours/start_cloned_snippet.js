/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

const countdownSnippet = {
    name: 'Countdown',
    id: 's_countdown',
};
const dragNDropOutOfFooter = wTourUtils.dragNDrop(countdownSnippet);
dragNDropOutOfFooter.run = 'drag_and_drop iframe #wrapwrap #wrap';

wTourUtils.registerEditionTour('website_start_cloned_snippet', {
    edition: true,
    test: true,
    url: '/',
}, [
    dragNDropOutOfFooter,
    wTourUtils.clickOnSnippet(countdownSnippet),
    {
        content: 'Click on clone snippet',
        trigger: '.oe_snippet_clone',
    },
    {
        content: 'Check that the cloned snippet has a canvas and that something has been drawn inside of it',
        trigger: 'iframe .s_countdown:eq(1) canvas',
        run: function () {
            // Check that at least one bit has been drawn in the canvas
            if (!this.$anchor[0].getContext('2d').getImageData(0, 0, 1000, 1000).data.includes(1)) {
                console.error('The cloned snippet should have been started');
            }
        },
    },
]);
