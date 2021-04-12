odoo.define("website.tour.edit_link_popover", function (require) {
"use strict";

const tour = require('web_tour.tour');
const wTourUtils = require('website.tour_utils');

tour.register('edit_link_popover', {
    test: true,
    url: '/?enable_editor=1',
}, [
    // 1. Test links in page content (web_editor)
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    {
        content: "Click on a paragraph",
        trigger: '#wrap .s_text_image p:nth-child(2)',
    },
    {
        content: "Click on 'Link' to open Link Dialog",
        extra_trigger: '#wrap .s_text_image p:nth-child(2)',
        trigger: "#toolbar #create-link",
    },
    {
        content: "Type the link URL",
        trigger: '#o_link_dialog_url_input',
        run: 'text /contactus'
    },
    {
        content: "Save the link by clickng on itself",
        trigger: '#wrap .s_text_image p:nth-child(2)',
    },
    {
        content: "Click on newly created link",
        trigger: '#wrap .s_text_image p:nth-child(2) a',
    },
    {
        content: "Popover should be shown",
        trigger: '.o_edit_menu_popover .o_we_url_link:contains("Contact Us")',
        run: function () {}, // it's a check
    },
    {
        content: "Click on Edit Link in Popover",
        trigger: '.o_edit_menu_popover .o_we_edit_link',
    },
    {
        content: "Type the link URL",
        trigger: '#o_link_dialog_url_input',
        run: "text /"
    },
    {
        content: "Save the link by clickng on itself",
        trigger: '#wrap .s_text_image p:nth-child(2)',
    },
    {
        content: "Click on link",
        trigger: '#wrap .s_text_image p:nth-child(2) a',
    },
    {
        content: "Popover should be shown with updated preview data",
        trigger: '.o_edit_menu_popover .o_we_url_link:contains("Home")',
        run: function () {}, // it's a check
    },
    {
        content: "Click on Remove Link in Popover",
        trigger: '.o_edit_menu_popover .o_we_remove_link',
    },
    {
        content: "Link should be removed",
        trigger: '#wrap .s_text_image p:nth-child(2):not(:has(a))',
        run: function () {}, // it's a check
    },
    // 2. Test links in navbar (website)
    {
        content: "Click navbar menu Home",
        trigger: '#top_menu a:contains("Home")',
    },
    {
        content: "Popover should be shown (2)",
        trigger: '.o_edit_menu_popover .o_we_url_link:contains("Home")',
        run: function () {}, // it's a check
    },
    {
        content: "Click on Edit Link in Popover",
        trigger: '.o_edit_menu_popover .o_we_edit_link',
    },
    {
        content: "Change the URL",
        trigger: '#o_link_dialog_url_input',
        run: "text /contactus"
    },
    {
        content: "Save the Link Dialog modal",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "Click on the Home menu again",
        trigger: '#top_menu a:contains("Home")',
        extra_trigger: '#top_menu a:contains("Home")[href="/contactus"]', // href should be changed
    },
    {
        content: "Popover should be shown with updated preview data",
        trigger: '.o_edit_menu_popover .o_we_url_link:contains("Contact Us")',
        run: function () {}, // it's a check
    },
    {
        content: "Click on Edit Menu in Popover",
        trigger: '.o_edit_menu_popover .js_edit_menu',
    },
    {
        content: "Edit Menu (tree) should open",
        trigger: '.js_add_menu',
        run: function () {}, // it's a check
    },
    {
        content: "Close modal",
        trigger: '.modal-footer .btn-secondary',
    },
    // 3. Test other links (CTA in navbar & links in footer)
    {
        content: "Click CTA in navbar",
        trigger: '#top_menu_container a.btn-primary[href="/contactus"]',
    },
    {
        content: "Popover should be shown (3)",
        trigger: '.o_edit_menu_popover .o_we_url_link:contains("Contact Us")',
        run: function () {}, // it's a check
    },
    {
        content: "Click 'Home' link in footer",
        trigger: 'footer a[href="/"]',
    },
    {
        content: "Popover should be shown (4)",
        trigger: '.o_edit_menu_popover .o_we_url_link:contains("Home")',
        run: function () {}, // it's a check
    },
    // 4. Popover should close when clicking non-link element
    {
        content: "Ensure popover is closed",
        trigger: 'footer h5',
    },
    // 5. Double click shouldn't do anything
    {
        content: "Double click on link",
        trigger: 'html:not(:has(.o_edit_menu_popover))', // popover should be closed
        run: function () {
            const $footerHomeLink = $('footer a[href="/"]').first();

            // Create range to simulate real double click, see pull request
            const range = document.createRange();
            range.selectNodeContents($footerHomeLink[0]);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);

            $footerHomeLink.click().dblclick();
        },
    },
    {
        content: "Ensure nothing happened on double click (except showing popover)",
        extra_trigger: 'html:not(:has(#o_link_dialog_url_input))',
        trigger: '.o_edit_menu_popover',
        run: function () {}, // it's a check
    },
]);
});
