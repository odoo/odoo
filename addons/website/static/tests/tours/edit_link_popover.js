import { registry } from "@web/core/registry";
import {
    insertSnippet,
    openLinkPopup,
    clickToolbarButton,
    waitForEditMode,
} from "@website/js/tours/tour_utils";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";

const FIRST_PARAGRAPH =
    ":iframe #wrap .s_text_image p:not([data-selection-placeholder]):nth-child(2)";

registry.category("web_tour.tours").add("edit_link_popover", {
    steps: () => [
        waitForEditMode,
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
        ...clickToolbarButton(
            "Paragraph",
            "#wrap .s_text_image p",
            "Insert link (Ctrl + K)",
            false
        ),
        {
            content: `Type the link URL /contactus`,
            trigger: ".o-we-linkpopover .o_we_href_input_link",
            run: `edit /contactus`,
        },
        {
            content: "Save the link by clicking on Apply button",
            trigger: ".o-we-linkpopover .o_we_apply_link",
            run: "click",
        },
        ...openLinkPopup({
            trigger: `${FIRST_PARAGRAPH} a`,
            url: "/contactus",
            label: "Contact Us",
            edit: "/",
        }),
        {
            content: "Remove paragraph selection",
            trigger: ":iframe body",
            async run() {
                const el = this.anchor;
                const sel = el.ownerDocument.getSelection();
                sel.removeAllRanges();
            },
        },
        ...openLinkPopup({
            trigger: `${FIRST_PARAGRAPH} a`,
            url: "/",
            label: "Home",
            remove: true,
        }),
        // 2. Test links in navbar (website)
        ...openLinkPopup({
            trigger: ":iframe .top_menu a:contains(Home)[href='/']",
            url: "/",
            label: "Home",
            runClick: false,
            edit: "/contactus",
        }),
        ...openLinkPopup({
            trigger: ":iframe .top_menu a:contains(Home)[href='/contactus']",
            url: "/contactus",
            label: "Contact Us",
        }),
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
        ...openLinkPopup({
            trigger: ":iframe #o_main_nav a.btn-primary:contains(Contact Us)",
            label: "Contact Us",
            url: "/contactus",
        }),
        ...openLinkPopup({
            trigger: ":iframe footer a:contains(Home)",
            label: "Home",
            url: "/",
        }),
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
        ...openLinkPopup({
            trigger: ":iframe footer a:contains(Home)",
            label: "Home",
            url: "/",
        }),
        {
            content: "Ensure that a click on the link popover link opens a new window in edit mode",
            trigger: ".o-we-linkpopover a.o_we_url_link[target='_blank']",
            async run({ click }) {
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
                await click();
            },
        },
        {
            content: "Ensure that link is opened correctly in edit mode",
            trigger: ".new_backend_window_opened",
        },
    ],
});
