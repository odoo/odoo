/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

const FIRST_PARAGRAPH = 'iframe #wrap .s_text_image p:nth-child(2)';

const clickFooter = [{
    content: "Save the link by clicking outside the URL input (not on a link element)",
    trigger: 'iframe footer h5:first',
}, {
    content: "Wait delayed click on footer",
    trigger: '.o_we_customize_panel we-title:contains("Footer")',
    run: function () {}, // it's a check
}];

const clickEditLink = [{
    content: "Click on Edit Link in Popover",
    trigger: 'iframe .o_edit_menu_popover .o_we_edit_link',
}, {
    content: "Ensure popover is closed",
    trigger: 'iframe html:not(:has(.o_edit_menu_popover))', // popover should be closed
    run: function () {}, // it's a check
    in_modal: false,
}];

wTourUtils.registerWebsitePreviewTour('edit_link_popover', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    // 1. Test links in page content (web_editor)
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    {
        content: "Click on a paragraph",
        trigger: FIRST_PARAGRAPH,
        run: 'text Paragraph', // Make sure the selection is set in the paragraph
    },
    {
        content: "Click on 'Link' to open Link Dialog",
        trigger: "#toolbar:not(.oe-floating) #create-link",
    },
    {
        content: "Type the link URL /contactus",
        trigger: '#o_link_dialog_url_input',
        run: 'text /contactus'
    },
    ...clickFooter,
    {
        content: "Click on newly created link",
        trigger: `${FIRST_PARAGRAPH} a`,
    },
    {
        content: "Popover should be shown",
        trigger: 'iframe .o_edit_menu_popover .o_we_url_link:contains("Contact Us")', // At this point preview is loaded
        run: function () {}, // it's a check
    },
    ...clickEditLink,
    {
        content: "Type the link URL /",
        trigger: '#o_link_dialog_url_input',
        run: "text /"
    },
    ...clickFooter,
    {
        content: "Click on link",
        trigger: `${FIRST_PARAGRAPH} a`,
    },
    {
        content: "Popover should be shown with updated preview data",
        trigger: 'iframe .o_edit_menu_popover .o_we_url_link:contains("Home")',
        run: function () {}, // it's a check
    },
    {
        content: "Click on Remove Link in Popover",
        trigger: 'iframe .o_edit_menu_popover .o_we_remove_link',
    },
    {
        content: "Link should be removed",
        trigger: `${FIRST_PARAGRAPH}:not(:has(a))`,
        run: function () {}, // it's a check
    },
    {
        content: "Ensure popover is closed",
        trigger: 'iframe html:not(:has(.o_edit_menu_popover))', // popover should be closed
        run: function () {}, // it's a check
    },
    // 2. Test links in navbar (website)
    {
        content: "Click navbar menu Home",
        trigger: 'iframe #top_menu a:contains("Home")',
    },
    {
        content: "Popover should be shown (2)",
        trigger: 'iframe .o_edit_menu_popover .o_we_url_link:contains("Home")',
        run: function () {}, // it's a check
    },
    ...clickEditLink,
    {
        content: "Change the URL",
        trigger: '#url_input',
        run: "text /contactus"
    },
    {
        content: "Save the Edit Menu modal",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "Click on the Home menu again",
        extra_trigger: 'div:not(.o_loading_dummy) > #oe_snippets',
        trigger: 'iframe #top_menu a:contains("Home")[href="/contactus"]',
    },
    {
        content: "Popover should be shown with updated preview data (2)",
        trigger: 'iframe .o_edit_menu_popover .o_we_url_link:contains("Contact Us")',
        run: function () {}, // it's a check
    },
    {
        content: "Click on Edit Menu in Popover",
        trigger: 'iframe .o_edit_menu_popover .js_edit_menu',
    },
    {
        content: "Edit Menu (tree) should open",
        trigger: '.o_website_dialog .oe_menu_editor',
        run: function () {}, // it's a check
    },
    {
        content: "Close modal",
        trigger: '.modal-footer .btn-secondary',
    },
    // 3. Test other links (CTA in navbar & links in footer)
    {
        content: "Click CTA in navbar",
        trigger: 'iframe #o_main_nav a.btn-primary[href="/contactus"]',
    },
    {
        content: "Popover should be shown (3)",
        trigger: 'iframe .o_edit_menu_popover .o_we_url_link:contains("Contact Us")',
        run: function () {}, // it's a check
    },
    {
        content: "Toolbar should be shown (3)",
        trigger: '.oe-toolbar:not(.oe-floating):has(#o_link_dialog_url_input:propValue(/contactus))',
        run: function () {}, // it's a check
    },
    {
        content: "Click 'Home' link in footer",
        trigger: 'iframe footer a[href="/"]',
    },
    {
        content: "Popover should be shown (4)",
        trigger: 'iframe .o_edit_menu_popover .o_we_url_link:contains("Home")',
        run: function () {}, // it's a check
    },
    {
        content: "Toolbar should be shown (4)",
        trigger: '.oe-toolbar:not(.oe-floating):has(#o_link_dialog_url_input:propValue(/))',
        run: function () {}, // it's a check
    },
    // 4. Popover should close when clicking non-link element
    ...clickFooter,
    // 5. Double click should not open popover but should open toolbar link
    {
        content: "Double click on link",
        extra_trigger: 'iframe html:not(:has(.o_edit_menu_popover))', // popover should be closed
        trigger: 'iframe footer a[href="/"]',
        run: function (actions) {
            // Create range to simulate real double click, see pull request
            const range = document.createRange();
            range.selectNodeContents(this.$anchor[0]);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            actions.click();
            actions.dblclick();
        },
    },
    {
        content: "Ensure popover is opened on double click, and so is right panel edit link",
        trigger: 'html:has(#o_link_dialog_url_input)',
        extra_trigger: 'iframe html:has(.o_edit_menu_popover)',
        run: function () {}, // it's a check
    },
    {
        content: "Ensure that a click on the link popover link opens a new window in edit mode",
        trigger: 'iframe .o_edit_menu_popover a.o_we_url_link[target="_blank"]',
        extra_trigger: 'iframe .o_edit_menu_popover a.o_we_full_url[target="_blank"]',
        run: (actions) => {
            // We do not want to open a link in a tour
            patch(browser, {
                open: (url) => {
                    if (window.location.hostname === url.hostname && url.pathname.startsWith('/@/')) {
                        document.querySelector('body').classList.add('new_backend_window_opened');
                    }
                }
            }, { pure: true });
            actions.click();
        },
    },
    {
        content: "Ensure that link is opened correctly in edit mode",
        trigger: '.new_backend_window_opened',
        run: () => {}, // it's a check
    },
]);
