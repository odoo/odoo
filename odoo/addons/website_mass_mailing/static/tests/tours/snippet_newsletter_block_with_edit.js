/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour('snippet_newsletter_block_with_edit', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    // Put a Newsletter block.
    wTourUtils.dragNDrop({
        id: 's_newsletter_block',
        name: 'Newsletter Block',
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
    ...wTourUtils.clickOnEditAndWaitEditMode(),
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
        trigger: '.dropdown:has([name="link_style_color"]) > button',
    },
    {
        content: 'Click on the primary style button',
        trigger: '[data-value="primary"]',
    },
    {
        content: 'Verify that the shape option is not available for primary while the size option appeared',
        trigger: 'we-customizeblock-option:not(:has([name="link_style_shape"]))',
        extra_trigger: 'we-customizeblock-option:has([name="link_style_size"])',
        isCheck: true,
    },
    {
        content: 'Click on the link style button',
        trigger: '.dropdown:has([name="link_style_color"]) > button',
    },
    {
        content: 'Click on the custom style button',
        trigger: '[data-value="custom"]',
    },
    {
        content: 'Change the shape of the button',
        trigger: '.dropdown:has([name="link_style_shape"]) > button',
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
        trigger: 'iframe .s_newsletter_block .js_subscribed_btn.btn.btn-custom.flat:not(.btn-success)',
        isCheck: true,
    },
]);
