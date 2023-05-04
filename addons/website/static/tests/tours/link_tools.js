/** @odoo-module */

import wTourUtils from 'website.tour_utils';

const clickOnImgStep = {
    content: "Click somewhere else to save.",
    trigger: 'iframe #wrap .s_text_image img',
};

wTourUtils.registerWebsitePreviewTour('link_tools', {
    test: true,
    url: '/',
    edition: true,
}, [
    // 1. Create a new link from scratch.
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    {
        content: "Replace first paragraph, to insert a new link",
        trigger: 'iframe #wrap .s_text_image p',
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
    // 2. Edit the link with the link tools.
    {
        content: "Click on the newly created link",
        trigger: 'iframe .s_text_image a[href="http://odoo.com"]:contains("odoo.com")',
    },
    {
        content: "Change content (editing the label input) to odoo website_2",
        trigger: '#o_link_dialog_label_input[value="odoo.com"]',
        run: 'text odoo website_2',
    },
    {
        content: "Click again on the link",
        trigger: 'iframe .s_text_image a[href="http://odoo.com"]:contains("odoo website_2")',
    },
    {
        content: "Change content (editing the DOM) to odoo website",
        trigger: 'iframe .s_text_image a[href="http://odoo.com"]:contains("odoo website_2")',
        run: 'text odoo website',
    },
    clickOnImgStep,
    {
        content: "Click again on the link",
        trigger: 'iframe .s_text_image a[href="http://odoo.com"]:contains("odoo website")',
    },
    {
        content: "Check that the label input contains the new content",
        trigger: '#o_link_dialog_label_input[value="odoo website"]',
        run: () => null, // it's a check
    },
    {
        content: "Link tools, should be open, change the url",
        trigger: '#o_link_dialog_url_input',
        run: 'text odoo.be'
    },

    clickOnImgStep,
    ...wTourUtils.clickOnSave(),
    // 3. Edit a link after saving the page.
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "The new link content should be odoo website and url odoo.be",
        trigger: 'iframe .s_text_image a[href="http://odoo.be"]:contains("odoo website")',
    },
    {
        content: "The new link content should be odoo website and url odoo.be",
        trigger: '#toolbar .dropdown:has([name="link_style_color"]) > button',
    },
    {
        // When doing automated testing, the link popover takes time to
        // hide. While hidding, the editor observer is unactive in order to
        // prevent the popover mutation to be recorded. In a manual
        // scenario, the popover has plenty of time to be hidden and the
        // obsever would be re-activated in time. As this problem arise only
        // in test, we make sure the popover is hidden
        trigger: 'iframe html:not(:has(.popover))',
        run: () => null, // it's a check
    },
    {
        content: "Click on the secondary style button.",
        trigger: '#toolbar we-button[data-value="secondary"]',
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "The link should have the secondary button style.",
        trigger: 'iframe .s_text_image a.btn.btn-secondary[href="http://odoo.be"]:contains("odoo website")',
        run: () => {}, // It's a check.
    },
    // 4. Add link on image.
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Click on image.",
        trigger: 'iframe .s_text_image img',
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
        trigger: 'iframe .s_text_image p',
    },
    {
        content: "Re-select image.",
        trigger: 'iframe .s_text_image img',
    },
    {
        content: "Check that link tools appear.",
        trigger: 'iframe .popover div a:contains("http://odoo.com")',
        run: () => {}, // It's a check.
    },
    // 5. Remove link from image.
    {
        content: "Remove link.",
        trigger: 'iframe .popover:contains("http://odoo.com") a .fa-chain-broken',
    },
    {
        content: "Check that image is not within a link anymore.",
        trigger: 'iframe .s_text_image div > img',
        run: () => {}, // It's a check.
    },
]);
