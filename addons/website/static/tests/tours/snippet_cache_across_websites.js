/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour('snippet_cache_across_websites', {
    edition: true,
    test: true,
    url: '/@/'
}, [
    {
        content: "Check that the custom snippet is displayed",
        trigger: '#snippet_custom_body span:contains("custom_snippet_test")',
        run: () => null,
    },
    // There's no need to save, but canceling might or might not show a popup...
    ...wTourUtils.clickOnSave(),
    {
        content: "Click on the website switch to switch to website 2",
        trigger: '.o_website_switcher_container button',
    },
    {
        content: "Switch to website 2",
        // Ensure data-website-id exists
        extra_trigger: 'iframe html[data-website-id="1"]',
        trigger: '.o_website_switcher_container .dropdown-item:contains("My Website 2")'
    },
    {
        content: "Wait for the iframe to be loaded",
        trigger: 'iframe html:not([data-website-id="1"])',
        run: () => null,
    },
    wTourUtils.clickOnEdit(),
    {
        content: "Check that the custom snippet is not here",
        extra_trigger: '#oe_snippets:not(:has(#snippet_custom_body span:contains("custom_snippet_test")))',
        trigger: '#oe_snippets:has(#snippet_custom.d-none)',
        run: () => null,
    },
]);
