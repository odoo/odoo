/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour('snippet_newsletter_block_with_edit', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    // Put a Newsletter block.
    ...wTourUtils.dragNDrop({
        id: 's_newsletter_block',
        name: 'Newsletter Block',
    }),
    {
        content: 'Wait for the list id to be set.',
        trigger: ':iframe .s_newsletter_block[data-list-id]:not([data-list-id="0"]) .s_newsletter_subscribe_form',
    },
    ...wTourUtils.clickOnSave(),
    // Subscribe to the newsletter.
    {
        trigger: ':iframe .s_newsletter_block input:value("admin@yourcompany.example.com")',
    },
    {
        content: 'Wait for the email to be loaded in the newsletter input',
        trigger: ':iframe .s_newsletter_block .js_subscribe_btn',
        run: "click",
    },
    // Change the link style.
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: 'Click on the Subscribe form',
        trigger: ':iframe .s_newsletter_block .s_newsletter_subscribe_form',
        run: "click",
    },
    {
        content: 'Toggle the option to display the Thanks button',
        trigger: 'we-button[data-toggle-thanks-message] we-checkbox',
        run: "click",
    },
    {
        content: 'Click on the Thanks button',
        trigger: ':iframe .s_newsletter_block .js_subscribed_btn',
        run: "click",
    },
    {
        content: 'Click on the link style button',
        trigger: '.dropdown:has([name="link_style_color"]) > button',
        run: "click",
    },
    {
        content: 'Click on the primary style button',
        trigger: '[data-value="primary"]',
        run: "click",
    },
    {
        trigger: 'we-customizeblock-option:has([name="link_style_size"])',
    },
    {
        content: 'Verify that the shape option is not available for primary while the size option appeared',
        trigger: 'we-customizeblock-option:not(:has([name="link_style_shape"]))',
    },
    {
        content: 'Click on the link style button',
        trigger: '.dropdown:has([name="link_style_color"]) > button',
        run: "click",
    },
    {
        content: 'Click on the custom style button',
        trigger: '[data-value="custom"]',
        run: "click",
    },
    {
        content: 'Change the shape of the button',
        trigger: '.dropdown:has([name="link_style_shape"]) > button',
        run: "click",
    },
    {
        content: 'Click on the flat shape button',
        trigger: '[data-value="flat"]',
        run: "click",
    },
    ...wTourUtils.clickOnSave(),
    // Check if the button style is correct (make sure that the 'btn-success'
    // class which is not suggested as a valid style in the editor panel did not
    // prevent to edit the button).
    {
        content: 'Check that the link style is correct',
        trigger: ':iframe .s_newsletter_block .js_subscribed_btn.btn.btn-custom.flat:not(.btn-success)',
    },
]);
