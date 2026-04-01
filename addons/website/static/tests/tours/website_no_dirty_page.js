import { browser } from "@web/core/browser/browser";
import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const makeSteps = (steps = []) => [
    ...insertSnippet({
        id: "s_text_image",
        name: "Text - Image",
        groupName: "Content",
    }),
    {
        content: "Click on Discard",
        trigger: ".o-snippets-top-actions [data-action='cancel']",
        run: "click",
    },
    {
        content: "Check that discarding actually warns when there are dirty changes, and cancel",
        trigger: ".modal-footer .btn-secondary",
        run: "click",
    },
    ...clickOnSave(),
    ...clickOnEditAndWaitEditMode(),
    {
        // This makes sure the last step about leaving edit mode at the end of
        // this tour makes sense.
        content: "Confirm we are in edit mode",
        trigger: ":iframe #wrapwrap.odoo-editor-editable",
    },
    ...steps,
    {
        // Makes sure the dirty flag does not happen after a setTimeout or
        // something like that.
        content: "Click elsewhere and wait for a few ms",
        trigger: ":iframe body",
        async run(actions) {
            actions.click();
            await new Promise((resolve) => {
                browser.setTimeout(() => {
                    document.body.classList.add("o_test_delay");
                    resolve();
                }, 999);
            });
        },
    },
    {
        trigger: "body.o_test_delay",
    },
    {
        content: "Click on Discard",
        trigger: ".o-snippets-top-actions [data-action='cancel']",
        run: "click",
    },
    {
        content: "Confirm we are not in edit mode anymore",
        trigger: ":iframe #wrapwrap:not(.odoo-editor-editable)",
    },
];

registerWebsitePreviewTour(
    "website_no_action_no_dirty_page",
    {
        url: "/",
        edition: true,
    },
    () => makeSteps()
);

registerWebsitePreviewTour(
    "website_no_dirty_page",
    {
        url: "/",
        edition: true,
    },
    () =>
        makeSteps([
            {
                // This has been known to mark the page as dirty because of the
                // "drag the column on image move" feature.
                content: "Click on default image",
                trigger: ":iframe .s_text_image img",
                run: "click",
            },
            {
                // There was a feature that auto-selected default text and was
                // known to break the dirty behavior. It was removed but it does
                // not hurt to still click on default text anyway.
                content: "Click on default paragraph",
                trigger: ":iframe .s_text_image h2 + p",
                run: "click",
            },
            {
                // Link edition was also known to break the dirty behavior.
                content: "Click on button",
                trigger: ":iframe .s_text_image .btn",
                async run(actions) {
                    await actions.click();
                    const el = this.anchor;
                    const sel = el.ownerDocument.getSelection();
                    sel.collapse(el, 0);
                    el.focus();
                },
            },
            {
                content:
                    "Add useless space at the end of the snippet class attribute, then click on it",
                trigger: ":iframe .s_text_image",
                async run(actions) {
                    this.anchor.setAttribute("class", this.anchor.getAttribute("class") + " ");
                    return actions.click();
                },
            },
        ])
);

registerWebsitePreviewTour(
    "website_no_dirty_lazy_image",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_text_image",
            name: "Text - Image",
            groupName: "Content",
        }),
        {
            // Ensure the test keeps testing what it should test (eg if we ever
            trigger: ':iframe img.o_lang_flag[loading="lazy"]',
        },
        {
            content: "Replace first paragraph, to insert a new link",
            // remove the lazy loading on those language img))
            trigger: ":iframe #wrap .s_text_image p",
            run: "editor SomeTestText",
        },
        {
            trigger: ':iframe #wrap .s_text_image p:contains("SomeTestText")',
        },
        {
            content: "Click elsewhere to be sure the editor fully process the new content",
            trigger: ":iframe #wrap .s_text_image img",
            run: "click",
        },
        {
            trigger: "[data-action-id='replaceMedia']",
        },
        {
            content: "Check that there is no more than one dirty flag",
            trigger: ":iframe body",
            run: function () {
                const dirtyCount = this.anchor.querySelectorAll(".o_dirty").length;
                if (dirtyCount !== 1) {
                    console.error(dirtyCount + " dirty flag(s) found");
                } else {
                    this.anchor.querySelector("#wrap").classList.add("o_dirty_as_expected");
                }
            },
        },
        {
            content: "Check previous step went through correctly about dirty flags",
            trigger: ":iframe #wrap.o_dirty_as_expected",
        },
    ]
);
