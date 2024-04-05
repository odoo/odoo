/** @odoo-module */

import tour from 'web_tour.tour';
import wTourUtils from 'website.tour_utils';

const clickOnImgStep = {
    content: "Click somewhere else to save.",
    trigger: '#wrap .s_text_image img',
};

tour.register('link_tools', {
    test: true,
    url: '/?enable_editor=1',
}, [
    // 1. Create a new link from scratch.
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    {
        content: "Replace first paragraph, to insert a new link",
        trigger: '#wrap .s_text_image p',
        run: 'text Go to odoo: '
    },
    {
        content: "Open link tools",
        trigger: "#toolbar #create-link",
    },
    {
        content: "Type the link URL odoo.com",
        trigger: '#o_link_dialog_url_input',
        run: 'text odoo.com'
    },
    clickOnImgStep,
    // Remove the link.
    {
        content: "Click on the newly created link",
        trigger: '.s_text_image a[href="http://odoo.com"]:contains("odoo.com")',
    },
    {
        content: "Remove the link.",
        trigger: '.popover:contains("http://odoo.com") a .fa-chain-broken',
    },
    {
        content: "Check that the link was removed",
        trigger: '#wrap .s_text_image p:contains("Go to odoo:"):not(:has(a))',
        run: () => {}, // It's a check.
    },
    // Recreate the link.
    {
        content: "Select first paragraph, to insert a new link",
        trigger: '#wrap .s_text_image p',
    },
    {
        content: "Open link tools",
        trigger: "#toolbar #create-link",
    },
    {
        content: "Type the link URL odoo.com",
        trigger: '#o_link_dialog_url_input',
        run: 'text odoo.com'
    },
    clickOnImgStep,
    // 2. Edit the link with the link tools.
    {
        content: "Click on the newly created link, change content to odoo website",
        trigger: '.s_text_image a[href="http://odoo.com"]:contains("odoo.com")',
        run: 'text odoo website',
    },
    {
        content: "Link tools, should be open, change the url",
        trigger: '#o_link_dialog_url_input',
        run: 'text odoo.be'
    },
    clickOnImgStep,
    ...wTourUtils.clickOnSave(),
    // 3. Edit a link after saving the page.
    wTourUtils.clickOnEdit(),
    {
        content: "The new link content should be odoo website and url odoo.be",
        extra_trigger: "#oe_snippets.o_loaded",
        trigger: '.s_text_image a[href="http://odoo.be"]:contains("odoo website")',
    },
    {
        content: "The new link content should be odoo website and url odoo.be",
        trigger: '#toolbar button[data-original-title="Link Style"]',
    },
    {
        content: "Click on the secondary style button.",
        trigger: '#toolbar we-button[data-value="secondary"]',
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "The link should have the secondary button style.",
        trigger: '.s_text_image a.btn.btn-secondary[href="http://odoo.be"]:contains("odoo website")',
        run: () => {}, // It's a check.
    },
    // 4. Add link on image.
    wTourUtils.clickOnEdit(),
    wTourUtils.dragNDrop({
        id: 's_three_columns',
        name: 'Columns',
    }),
    {
        content: "Click on the first image.",
        trigger: '.s_three_columns .row > :nth-child(1) img',
        extra_trigger: '#oe_snippets.o_loaded',
    },
    {
        content: "Activate link.",
        trigger: '.o_we_customize_panel we-row:contains("Media") we-button.fa-link',
    },
    {
        content: "Set URL.",
        trigger: '.o_we_customize_panel we-input:contains("Your URL") input',
        run: 'text odoo.com',
    },
    {
        content: "Deselect image.",
        trigger: '.s_three_columns .row > :nth-child(2) img',
    },
    {
        content: "Re-select image.",
        trigger: '.s_three_columns .row > :nth-child(1) img',
    },
    {
        content: "Check that the second image is not within a link.",
        trigger: '.s_three_columns .row > :nth-child(2) div > img',
        run: () => {}, // It's a check.
    },
    {
        content: "Check that link tools appear.",
        trigger: '.popover div a:contains("http://odoo.com")',
        run: () => {}, // It's a check.
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the first image was saved.",
        trigger: '.s_three_columns .row > :nth-child(1) div > a > img',
        run: () => {}, // It's a check.
    },
    {
        content: "Check that the second image was saved.",
        trigger: '.s_three_columns .row > :nth-child(2) div > img',
        run: () => {}, // It's a check.
    },
    // 5. Remove link from image.
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Reselect the first image.",
        trigger: '.s_three_columns .row > :nth-child(1) div > a > img',
    },
    {
        content: "Check that link tools appear.",
        trigger: '.popover div a:contains("http://odoo.com")',
        run: () => {}, // It's a check.
    },
    {
        content: "Remove link.",
        trigger: '.popover:contains("http://odoo.com") a .fa-chain-broken',
    },
    {
        content: "Check that image is not within a link anymore.",
        trigger: '.s_three_columns .row > :nth-child(1) div > img',
        run: () => {}, // It's a check.
    },
]);
