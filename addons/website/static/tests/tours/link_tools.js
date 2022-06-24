/** @odoo-module */

import wTourUtils from 'website.tour_utils';

const clickOnImgStep = {
    content: "Click somewhere else to save.",
    trigger: 'iframe #wrap .s_text_image img',
};

wTourUtils.registerEditionTour('link_tools', {
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
        content: "Click on the newly created link, change content to odoo website",
        trigger: 'iframe .s_text_image a[href="http://odoo.com"]:contains("odoo.com")',
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
        trigger: 'iframe .s_text_image a[href="http://odoo.be"]:contains("odoo website")',
    },
    {
        content: "The new link content should be odoo website and url odoo.be",
        trigger: '#toolbar button[data-original-title="Link Style"]',
    },
    {
        // When doing automated testing, the link popover takes time to
        // hide. While hidding, the editor observer is unactive in order to
        // prevent the popover mutation to be recorded. In a manual
        // scenario, the popover has plenty of time to be hidden and the
        // obsever would be re-activated in time. As this problem arise only
        // in test, we make sure the popover is hidden
        trigger: '.o_website_preview:not(:has(.popover))',
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
    }
]);
