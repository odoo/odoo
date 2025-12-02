import {
    insertSnippet,
    registerWebsitePreviewTour,
    openLinkPopup,
    clickToolbarButton,
} from "@website/js/tours/tour_utils";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

const FIRST_PARAGRAPH = ":iframe #wrap .s_text_image p:not([data-selection-placeholder]):nth-child(2)";

const clickEditLink = {
    content: "Click on Edit Link in Popover",
    trigger: ".o-we-linkpopover .o_we_edit_link",
    run: "click",
};

const editLinkAndApply = (url) => [
    {
        content: `Type the link URL ${url}`,
        trigger: ".o-we-linkpopover .o_we_href_input_link",
        run: `edit ${url}`,
    },
    {
        content: "Save the link by clicking on Apply button",
        trigger: ".o-we-linkpopover .o_we_apply_link",
        run: "click",
    },
];

registerWebsitePreviewTour(
    "edit_link_popover",
    {
        url: "/",
        edition: true,
    },
    () => [
        // 1. Test links in page content (web_editor)
        ...insertSnippet({
            id: "s_text_image",
            name: "Text - Image",
            groupName: "Content",
        }),
        {
            content: "Click on a paragraph",
            trigger: FIRST_PARAGRAPH,
            run: "editor Paragraph", // Make sure the selection is set in the paragraph
        },
        ...clickToolbarButton("Paragraph", "#wrap .s_text_image p", "Add a link", false),
        ...editLinkAndApply("/contactus"),
        ...openLinkPopup(`${FIRST_PARAGRAPH} a`, "/contactus", 1, true),
        {
            content: "Popover should be shown for contact us",
            trigger: ".o-we-linkpopover .o_we_url_link:contains('Contact Us')",
        },
        clickEditLink,
        ...editLinkAndApply("/"),
        {
            content: "Remove paragraph selection",
            trigger: ":iframe body",
            async run() {
                const el = this.anchor;
                const sel = el.ownerDocument.getSelection();
                sel.removeAllRanges();
            },
        },
        ...openLinkPopup(`${FIRST_PARAGRAPH} a`, "/", 1, true),
        {
            content: "Popover should be shown for home",
            trigger: ".o-we-linkpopover .o_we_url_link:contains('Home')",
        },
        clickEditLink,
        {
            content: "Click on Remove Link in Popover",
            trigger: ".o-we-linkpopover .o_we_remove_link",
            run: "click",
        },
        {
            content: "Link should be removed",
            trigger: `${FIRST_PARAGRAPH}:not(:has(a))`,
        },
        {
            content: "Ensure popover is closed",
            trigger: ".o-overlay-container:not(:visible:has(.o-we-linkpopover))", // popover should be closed
        },
        // 2. Test links in navbar (website)
        {
            content: "Click navbar menu Home",
            trigger: ':iframe .top_menu a:contains("Home")',
            run: "click",
        },
        ...openLinkPopup(":iframe #o_main_nav a.nav-link:contains('Home')", "/contactus", 1, false),
        {
            content: "Popover should be shown (2)",
            trigger: ".o-we-linkpopover .o_we_url_link:contains('Home')",
        },
        clickEditLink,
        {
            content: "Change the URL",
            trigger: ".modal-dialog #url_input",
            run: "edit /contactus",
        },
        {
            content: "Save the Edit Menu modal",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        ...openLinkPopup(
            ":iframe .top_menu a:contains('Home')[href='/contactus']",
            "/contactus",
            0,
            true
        ),
        {
            content: "Popover should be shown with updated preview data (2)",
            trigger: ".o-we-linkpopover .o_we_url_link:contains('Contact Us')",
        },
        {
            content: "Click on Edit Menu in Popover",
            trigger: ".o-we-linkpopover .js_edit_menu",
            run: "click",
        },
        {
            content: "Edit Menu (tree) should open",
            trigger: ".o_website_dialog .oe_menu_editor",
        },
        {
            content: "Close modal",
            trigger: ".modal-footer .btn-secondary",
            run: "click",
        },
        {
            content: "Check that the modal is closed",
            trigger: ":iframe html:not(.modal-body)",
        },
        // 3. Test other links (CTA in navbar & links in footer)
        ...openLinkPopup(":iframe #o_main_nav a.btn-primary[href='/contactus']", "CTA", 1, true),
        {
            content: "Popover should be shown (3)",
            trigger: ".o-we-linkpopover .o_we_url_link:contains('Contact Us')",
        },
        ...openLinkPopup(":iframe footer a[href='/']", "Footer Home", 1, true),
        {
            content: "Popover should be shown (4)",
            trigger: ".o-we-linkpopover .o_we_url_link:contains('Home')",
        },
        // 4. Popover should close when clicking non-link element
        {
            content: "Click outside the link popover",
            trigger: ":iframe body",
            run: "click",
        },
        {
            content: "Ensure popover is closed",
            trigger: ".o-overlay-container:not(:visible:has(.o-we-linkpopover))", // popover should be closed
        },
        // 5. Double click should not open popover but should open toolbar link
        {
            content: "Double click on link",
            trigger: ':iframe footer a[href="/"]',
            async run(actions) {
                // Create range to simulate real double click, see pull request
                const el = this.anchor;
                const sel = el.ownerDocument.getSelection();
                sel.collapse(el.childNodes[1], 1);
                await actions.click();
                await actions.dblclick();
            },
        },
        {
            content: "Ensure that the link toolbar is opened",
            trigger: ".o-we-toolbar button[name='link']",
        },
        {
            content: "Click on the link from toolbar",
            trigger: ".o-we-toolbar",
            run: "click",
        },
        // 6. Test link popover link opens a new window in edit mode
        ...openLinkPopup(":iframe footer a[href='/']", "Footer Home", 1, true),
        {
            content: "Ensure that a click on the link popover link opens a new window in edit mode",
            trigger: ".o-we-linkpopover a.o_we_url_link[target='_blank']",
            run(actions) {
                // We do not want to open a link in a tour
                patch(
                    browser,
                    {
                        open(url) {
                            if (
                                window.location.hostname === url.hostname &&
                                url.pathname.startsWith("/@/")
                            ) {
                                document
                                    .querySelector("body")
                                    .classList.add("new_backend_window_opened");
                            }
                        },
                    },
                    { pure: true }
                );
                actions.click();
            },
        },
        {
            content: "Ensure that link is opened correctly in edit mode",
            trigger: ".new_backend_window_opened",
        },
    ]
);
