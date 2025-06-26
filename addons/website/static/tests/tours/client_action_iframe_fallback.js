/** @odoo-module */

import { registerWebsitePreviewTour } from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('client_action_iframe_fallback', {
    url: '/',
},
() => [
    {
        content: "Ensure we are on the expected page",
        trigger: ':iframe html[data-view-xmlid="website.homepage"]',
    }, {
        content: "Ensure the iframe fallback is not loaded in test mode",
        trigger: 'body',
        run() {
            if (document.querySelector('iframe[src="/website/iframefallback"]')) {
                throw new Error("The iframe fallback shouldn't be inside the DOM.");
            }
        },
    },
]);
