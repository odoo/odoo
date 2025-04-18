import {
    insertSnippet,
    openLinkPopup,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const FIRST_PARAGRAPH = ":iframe #wrap .s_text_image p:nth-child(2)";
const SECOND_PARAGRAPH = ":iframe #wrap .s_text_image p:nth-child(3)";

const applyLinkAndClickBody = [
    {
        content: "Save the link by clicking on Apply button",
        trigger: ".o-we-linkpopover .o_we_apply_link",
        run: "click",
    },
    // Need to select something else otherwise clicking on same link after creation
    // doesn't open link popover.
    {
        content: `Click on outside to select something else`,
        trigger: `${SECOND_PARAGRAPH}`,
        async run() {
            const el = this.anchor;
            const sel = el.ownerDocument.getSelection();
            sel.collapse(el.childNodes[1], 1);
            el.focus();
        },
    },
];

const clickEditLink = [
    {
        content: "Click on Edit Link in Popover",
        trigger: ".o-we-linkpopover .o_we_edit_link",
        run: "click",
    },
];

const clickOnParagraph = (trigger) => [
    {
        content: "Click on a paragraph",
        trigger: trigger,
        async run(actions) {
            const range = document.createRange();
            const selection = this.anchor.ownerDocument.getSelection();
            range.selectNodeContents(this.anchor);
            selection.removeAllRanges();
            selection.addRange(range);
            await actions.click();
        },
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
        ...clickOnParagraph(FIRST_PARAGRAPH),
        {
            content: "Click on 'Link' to open Link Dialog",
            trigger: ".o-we-toolbar button[name='link']",
            run: "click",
        },
        {
            content: "Type the link URL /contactus",
            trigger: ".o-we-linkpopover .o_we_href_input_link",
            run: "edit /contactus",
        },
        ...applyLinkAndClickBody,
        ...openLinkPopup(`${FIRST_PARAGRAPH} a`, "newly created", 1, true),
        {
            content: "Popover should be shown",
            trigger: '.o-we-linkpopover .o_we_url_link:contains("Contact Us")',
        },
        ...clickEditLink,
        {
            content: "Type the link URL /",
            trigger: ".o-we-linkpopover .o_we_href_input_link",
            run: `edit /`,
        },
        ...applyLinkAndClickBody,
        ...openLinkPopup(`${FIRST_PARAGRAPH} a`, "", 1, true),
        {
            content: "Popover should be shown with updated preview data",
            trigger: '.o-we-linkpopover .o_we_url_link:contains("Home")',
        },
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
        ...clickOnParagraph(":iframe #o_main_nav a.nav-link:contains('Home')"),
        {
            content: "Click on 'Link' to open Link Dialog",
            trigger: ".o-we-toolbar button[name='link']",
            run: "click",
        },
        {
            content: "Popover should be shown (2)",
            trigger: ".o-we-linkpopover .o_we_url_link:contains('Home')",
        },
        ...clickEditLink,
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
        {
            trigger: ".o-snippets-menu",
        },
        ...openLinkPopup(`:iframe .top_menu a:contains("Home")[href="/contactus"]`, "", 0, true),
        {
            content: "Popover should be shown with updated preview data (2)",
            trigger: '.o-we-linkpopover .o_we_url_link:contains("Contact Us")',
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
        ...openLinkPopup(`:iframe #o_main_nav a.btn-primary[href="/contactus"]`, "CTA", 0, true),
        {
            content: "Popover should be shown (3)",
            trigger: '.o-we-linkpopover .o_we_url_link:contains("Contact Us")',
        },
        ...openLinkPopup(`:iframe footer a[href="/"]`, "footer Home", 1, true),
        {
            content: "Popover should be shown (4)",
            trigger: '.o-we-linkpopover .o_we_url_link:contains("Home")',
        },
        // 4. Popover should close when clicking non-link element
        {
            content: "Wait delayed click on body",
            trigger: ":iframe body",
            run: "click",
        },
        {
            content: "Ensure popover is closed",
            trigger: ".o-overlay-container:not(:visible:has(.o-we-linkpopover))", // popover should be closed
        },
    ]
);
