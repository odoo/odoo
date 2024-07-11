/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour('client_action_iframe_fallback', {
    test: true,
    url: '/',
},
() => [
    {
        content: "Ensure we are on the expected page",
        trigger: 'body iframe html[data-view-xmlid="website.homepage"]',
        run: () => {}, // It's a check.
    }, {
        content: "Ensure the iframe fallback is not loaded in test mode",
        trigger: 'body',
        run: () => {
            if (document.querySelector('iframe[src="/website/iframefallback"]')) {
                console.error("The iframe fallback shouldn't be inside the DOM.");
            }
        },
    },
]);
