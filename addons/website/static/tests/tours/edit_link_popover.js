/** @odoo-module **/

import {
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { waitFor } from "@odoo/hoot-dom";

const FIRST_PARAGRAPH = ':iframe #wrap .s_text_image p:nth-child(2)';

const clickFooter = [{
    content: "Save the link by clicking outside the URL input (not on a link element)",
    trigger: ':iframe footer h5:first',
    run: "click",
}, {
    content: "Wait delayed click on footer",
    trigger: '.o_we_customize_panel we-title:contains("Footer")',
}];

const clickEditLink = [{
    content: "Click on Edit Link in Popover",
    trigger: ':iframe .o_edit_menu_popover .o_we_edit_link',
    run: "click",
}, {
    content: "Ensure popover is closed",
    trigger: ':iframe html:not(:has(.o_edit_menu_popover))', // popover should be closed
}];

registerWebsitePreviewTour('edit_link_popover_1', {
    url: '/',
    edition: true,
}, () => [
    // 1. Test links in page content (web_editor)
    ...insertSnippet({
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    }),
    {
        content: "Click on a paragraph",
        trigger: FIRST_PARAGRAPH,
        run: "editor Paragraph", // Make sure the selection is set in the paragraph
    },
    {
        content: "Click on 'Link' to open Link Dialog",
        trigger: "#toolbar:not(.oe-floating) #create-link",
        run: "click",
    },
    {
        content: "Type the link URL /contactus",
        trigger: '#o_link_dialog_url_input',
        run: "edit /contactus",
    },
    ...clickFooter,
    {
        content: "Click on newly created link",
        trigger: `${FIRST_PARAGRAPH} a`,
        run: "click",
    },
    {
        content: "Popover should be shown",
        trigger: ':iframe .o_edit_menu_popover .o_we_url_link:contains("Contact Us")', // At this point preview is loaded
    },
    ...clickEditLink,
    {
        content: "Type the link URL /",
        trigger: '#o_link_dialog_url_input',
        run: `edit /`,
    },
    ...clickFooter,
    {
        content: "Click on link",
        trigger: `${FIRST_PARAGRAPH} a`,
        run: "click",
    },
    {
        content: "Popover should be shown with updated preview data",
        trigger: ':iframe .o_edit_menu_popover .o_we_url_link:contains("Home")',
    },
    {
        content: "Click on Remove Link in Popover",
        trigger: ':iframe .o_edit_menu_popover .o_we_remove_link',
        run: "click",
    },
    {
        content: "Link should be removed",
        trigger: `${FIRST_PARAGRAPH}:not(:has(a))`,
    },
    {
        content: "Ensure popover is closed",
        trigger: ':iframe html:not(:has(.o_edit_menu_popover))', // popover should be closed
    },
    // 2. Test links in navbar (website)
    {
        content: "Click navbar menu Home",
        trigger: ':iframe .top_menu a:contains("Home")',
        run: "click",
    },
    {
        content: "Popover should be shown (2)",
        trigger: ':iframe .o_edit_menu_popover .o_we_url_link:contains("Home")',
    },
    ...clickEditLink,
    {
        content: "Change the URL",
        trigger: '#url_input',
        run: "edit /contactus",
    },
    {
        content: "Save the Edit Menu modal",
        trigger: '.modal-footer .btn-primary',
        run: "click",
    },
    {
        trigger: "div:not(.o_loading_dummy) > #oe_snippets",
    },
    {
        content: "Click on the Home menu again",
        trigger: ':iframe .top_menu a:contains("Home")[href="/contactus"]',
        run: "click",
    },
    {
        content: "Popover should be shown with updated preview data (2)",
        trigger: ':iframe .o_edit_menu_popover .o_we_url_link:contains("Contact Us")',
    },
    {
        content: "Click on Edit Menu in Popover",
        trigger: ':iframe .o_edit_menu_popover .js_edit_menu',
        run: "click",
    },
    {
        content: "Edit Menu (tree) should open",
        trigger: '.o_website_dialog .oe_menu_editor',
    },
    {
        content: "Close modal",
        trigger: '.modal-footer .btn-secondary',
        run: "click",
    },
    {
        content: "Check that the modal is closed",
        trigger: ":iframe html:not(.modal-body)",
    }
]);

registerWebsitePreviewTour('edit_link_popover_2', {
    url: '/',
    edition: true,
}, () => [
    // 1. Test links in page content (web_editor)
    ...insertSnippet({
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    }),
    // 3. Test other links (CTA in navbar & links in footer)
    {
        content: "Click CTA in navbar",
        trigger: ':iframe .o_main_nav a.btn-primary[href="/contactus"]',
        run: "click",
    },
    {
        content: "Popover should be shown (3)",
        trigger: ':iframe .o_edit_menu_popover .o_we_url_link:contains("Contact Us")',
    },
    {
        content: "Toolbar should be shown (3)",
        trigger: `.oe-toolbar:not(.oe-floating):has(#o_link_dialog_url_input:value('/contactus'))`,
    },
    {
        content: "Click 'Home' link in footer",
        trigger: ':iframe footer a[href="/"]',
        run(helpers) {
            helpers.click();
            waitFor(`:iframe .o_edit_menu_popover .o_we_url_link:contains("Home")`, { timeout: 5000 });
        }
    },
    {
        content: "Toolbar should be shown (4)",
        trigger: `.oe-toolbar:not(.oe-floating):has(#o_link_dialog_url_input:value('/'))`,
    },
    // 4. Popover should close when clicking non-link element
    ...clickFooter,
    // 5. Double click should not open popover but should open toolbar link
    {
        trigger: ":iframe html:not(:has(.o_edit_menu_popover))", // popover should be closed
    },
    {
        content: "Double click on link",
        trigger: ':iframe footer a[href="/"]',
        async run(actions) {
            // Create range to simulate real double click, see pull request
            const range = document.createRange();
            range.selectNodeContents(this.anchor);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            await actions.click();
            await actions.dblclick();
        },
    },
    {
        trigger: ":iframe html:has(.o_edit_menu_popover)",
    },
    {
        content: "Ensure popover is opened on double click, and so is right panel edit link",
        trigger: 'html:has(#o_link_dialog_url_input)',
    },
    {
        trigger: ':iframe .o_edit_menu_popover a.o_we_full_url[target="_blank"]',
    },
    {
        content: "Ensure that a click on the link popover link opens a new window in edit mode",
        trigger: ':iframe .o_edit_menu_popover a.o_we_url_link[target="_blank"]',
        run(actions) {
            // We do not want to open a link in a tour
            patch(browser, {
                open(url) {
                    if (window.location.hostname === url.hostname && url.pathname.startsWith('/@/')) {
                        document.querySelector('body').classList.add('new_backend_window_opened');
                    }
                }
            }, {pure: true});
            actions.click();
        },
    },
    {
        content: "Ensure that link is opened correctly in edit mode",
        trigger: '.new_backend_window_opened',
    },
]);
