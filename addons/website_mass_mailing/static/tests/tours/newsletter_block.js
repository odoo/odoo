/** @odoo-module */

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour('newsletter_block_edition', {
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
        trigger: '.dropdown:has([name="link_style_color"]) > button',
    },
    {
        content: 'Click on the primary style button',
        trigger: '[data-value="primary"]',
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
        trigger: 'iframe .s_newsletter_block .js_subscribed_btn.btn.btn-primary.flat:not(.btn-success)',
    },
]);

// 4-part test

wTourUtils.registerWebsitePreviewTour('newsletter_block_invalid_list_setup', {
    test: true,
    url: '/',
    edition: true,
}, [
    wTourUtils.dragNDrop({
        id: 's_newsletter_block',
        name: 'Newsletter block',
    }),
    {
        content: 'Select the "customize" options',
        trigger: '.o_we_customize_snippet_btn',
    },
    {
        content: 'Select the block',
        trigger: 'iframe .s_newsletter_block:not([data-list-id="0"])',
    },
    {
        content: 'Select listId ("Newsletter") options',
        trigger: 'we-select[data-attribute-name="listId"]',
    },
    {
        content: 'Pick list with id 1',
        trigger: 'we-select[data-attribute-name="listId"] we-button[data-select-data-attribute="1"]',
    },
    {
        content: 'Wait for the list id to be set.',
        trigger: 'iframe .s_newsletter_block[data-list-id="1"]',
        run: () => null,
    },
    ...wTourUtils.clickOnSave(),
    { // Make sure the check has run before checking that it didn't add a div (as the div does not exist by default before the check)
        content: 'Check that the warning is set',
        trigger: 'iframe .s_newsletter_block[data-list-id="1"] .s_newsletter_subscription_checked',
        run: function () {
            // Check that at least one bit has been drawn in the canvas
            if (document.querySelector('.s_newsletter_block[data-list-id="1"] div.alert-warning')) {
                console.error('There should not be any warning yet. Contact list 1 should still exist.');
            }
        },
    },
]);

wTourUtils.registerWebsitePreviewTour('newsletter_block_invalid_list_internal_user_no_change', {
    test: true,
    url: '/',
    edition: false,
}, [
    {
        content: 'Warning is set',
        trigger: 'iframe .s_newsletter_block[data-list-id="1"] div.alert-warning',
        run: () => null,
    },
    wTourUtils.clickOnEdit(),
    {
        content: 'Warning is removed in edit mode',
        trigger: 'iframe .s_newsletter_block[data-list-id="1"] .s_newsletter_subscription_checked',
        run: () => {
            // Check that at least one bit has been drawn in the canvas
            if (document.querySelector('.s_newsletter_block[data-list-id="1"] div.alert-warning')) {
                console.error('Warning text should have disappeared when the edit mode was switched on.');
            }
        },
    },
    ...wTourUtils.clickOnSave(),
    {
        content: 'Warning remain after saving if still invalid',
        trigger: 'iframe .s_newsletter_block[data-list-id="1"] div.alert-warning',
        run: () => null,
    },
]);

wTourUtils.registerWebsitePreviewTour('newsletter_block_invalid_list_public_user', {
    test: true,
    url: '/',
    edition: false,
}, [
    { // we are redirected to login page after logging out
        content: 'Go to the website (move from login page if we are there)',
        trigger: '#top_menu_container a[href="/"]'
    },
    {
        content: 'Warning not displayed for public users',
        trigger: '.s_newsletter_block[data-list-id="1"] .s_newsletter_subscription_checked',
        run: () => {
            // Check that at least one bit has been drawn in the canvas
            if (document.querySelector('.s_newsletter_block[data-list-id="1"] div.alert-warning')) {
                console.error('Warning text should not appear for public users.');
            }
        },
    },
]);


wTourUtils.registerWebsitePreviewTour('newsletter_block_invalid_list_internal_user_with_change', {
    test: true,
    url: '/',
    edition: false,
}, [
    {
        content: 'Warning is set',
        trigger: 'iframe .s_newsletter_block[data-list-id="1"] div.alert-warning',
        run: () => null,
    },
    wTourUtils.clickOnEdit(),
    {
        content: 'Select the block',
        trigger: 'iframe .s_newsletter_block[data-list-id="1"]',
    },
    {
        content: 'Select the "customize" options',
        trigger: '.o_we_customize_snippet_btn',
    },
    {
        content: 'Reselect the block',
        trigger: 'iframe .s_newsletter_block[data-list-id="1"]',
    },
    {
        content: 'Select listId ("Newsletter") options',
        trigger: 'we-select[data-attribute-name="listId"]',
    },
    {
        content: 'Pick a valid option',
        trigger: 'we-select[data-attribute-name="listId"] we-button[data-select-data-attribute="2"]',
    },
    ...wTourUtils.clickOnSave(),
    {
        content: 'Warning is removed in edit mode',
        trigger: 'iframe .s_newsletter_block[data-list-id="2"] .s_newsletter_subscription_checked',
        run: () => {
            if (document.querySelector('.s_newsletter_block:not([data-list-id="2"]) div.alert-warning')) {
                console.error('Warning text should have disappeared when the edit mode was switched on.');
            }
        },
    },
]);
