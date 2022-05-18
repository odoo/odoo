/** @odoo-module */

import tour from 'web_tour.tour';
import wTourUtils from 'website.tour_utils';

tour.register('newsletter_block_edition', {
    test: true,
    url: '/?enable_editor=1',
}, [
    // Put a Newsletter block.
    wTourUtils.dragNDrop({
        id: 's_newsletter_block',
        name: 'Newsletter block',
    }),
    {
        content: 'Wait for the list id to be set.',
        trigger: '.s_newsletter_subscribe_form[data-list-id]:not([data-list-id="0"])',
    },
    ...wTourUtils.clickOnSave(),
    // Subscribe to the newsletter.
    {
        content: 'Wait for the email to be loaded in the newsletter input',
        trigger: '.s_newsletter_block .js_subscribe_btn',
        extra_trigger: '.s_newsletter_block input:propValue(admin@yourcompany.example.com)',
    },
    // Change the link style.
    wTourUtils.clickOnEdit(),
    {
        content: 'Wait for the editor to be fully started',
        trigger: '#oe_snippets',
    },
    {
        content: 'Click on the Thanks button',
        trigger: '.s_newsletter_block .js_subscribed_btn',
    },
    {
        content: 'Click on the link style button',
        trigger: '[data-original-title="Link Style"]',
    },
    {
        content: 'Click on the primary style button',
        trigger: '[data-value="primary"]',
    },
    {
        content: 'Change the shape of the button',
        trigger: '[data-original-title="Link Shape"]',
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
        trigger: '.s_newsletter_block .js_subscribed_btn.btn.btn-primary.flat:not(.btn-success)',
    },
]);
