/** @odoo-module */

import wTourUtils from 'website.tour_utils';

wTourUtils.registerEditionTour('newsletter_block_edition', {
    test: true,
    url: '/',
    edition: true,
}, [
    // Put a Newsletter block.
    wTourUtils.dragNDrop({
        id: 's_newsletter_block',
        name: 'Newsletter block',
    }),
    {
        content: 'Wait for the list id to be set.',
        trigger: 'iframe .s_newsletter_block[data-list-id]:not([data-list-id="0"]) .s_newsletter_subscribe_form',
        run: () => null, // it's a check
    },
    ...wTourUtils.clickOnSave(),
    // Subscribe to the newsletter.
    {
        content: 'Wait for the email to be loaded in the newsletter input',
        trigger: 'iframe .s_newsletter_block .js_subscribe_btn',
        extra_trigger: 'iframe .s_newsletter_block input:propValue(admin@yourcompany.example.com)',
    },
    // Change the link style.
    wTourUtils.clickOnEdit(),
    {
        content: 'Click on the Subscribe button',
        trigger: 'iframe .s_newsletter_block .js_subscribe_btn',
    },
    {
        content: 'Toggle the option to display the Thanks button',
        trigger: 'we-button[data-toggle-thanks-button] we-checkbox',
    },
    {
        content: 'Click on the Thanks button',
        trigger: 'iframe .s_newsletter_block .js_subscribed_btn',
    },
    {
        content: 'Click on the link style button',
        trigger: '[data-bs-original-title="Link Style"]',
    },
    {
        content: 'Click on the primary style button',
        trigger: '[data-value="primary"]',
    },
    {
        content: 'Change the shape of the button',
        trigger: '[data-bs-original-title="Link Shape"]',
    },
    {
        content: 'Click on the flat shape button',
        trigger: '[data-value="flat"]',
    },
    ...wTourUtils.clickOnSave(),
    // Check if the button style is correct (make sure that the 'btn-success'
    // class which is not suggested as a valid style in the editor panel did not
    // prevent to edit the button).
    {
        content: 'Check that the link style is correct',
        trigger: 'iframe .s_newsletter_block .js_subscribed_btn.btn.btn-primary.flat:not(.btn-success)',
    },
]);
