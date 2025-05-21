import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";
import { patch } from "@web/core/utils/patch";

// Opening the system's file selector is not possible programmatically, so we
// mock the upload service.
let unpatch;
const patchStep = {
    content: "Patch upload service",
    trigger: "body",
    run: () => {
        const uploadService = odoo.__WOWL_DEBUG__.root.env.services.uploadLocalFiles;
        unpatch = patch(uploadService, {
            async upload() {
                return [{ id: 1, name: "file.txt", public: true, checksum: "123" }];
            },
        });
    },
};
const unpatchStep = {
    content: "Unpatch upload service",
    trigger: "body",
    run: () => unpatch(),
};

function showLinkPopover(linkEl) {
    const doc = linkEl.ownerDocument;
    const selection = doc.getSelection();
    const range = doc.createRange();
    selection.removeAllRanges();
    range.setStart(linkEl.childNodes[0], 0);
    range.setEnd(linkEl.childNodes[0], 0);
    doc.dispatchEvent(new Event("focus"));
    selection.addRange(range);
}

/**
 * The purpose of this tour is to check the Linktools to create a link to an
 * uploaded document.
 */
registerWebsitePreviewTour(
    "test_link_to_document",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            name: "Banner",
            id: "s_banner",
            groupName: "Intro",
        }),
        {
            content: "Click on button Start Now",
            trigger: ":iframe #wrap .s_banner a:nth-child(1)",
            run: ({ anchor }) => {
                showLinkPopover(anchor);
            },
        },
        {
            content: "Click on edit link",
            trigger: ".o-we-linkpopover .o_we_edit_link",
            run: "click",
        },
        {
            content: "Make upload button appear by emptying the link input",
            trigger: ".o_we_href_input_link",
            run: ({ anchor }) => {
                anchor.value = "";
                anchor.dispatchEvent(new Event("input"));
            },
        },
        patchStep,
        {
            content: "Click on upload button",
            trigger: ".o_we_href_input_link + span button",
            run: "click",
        },
        {
            content: "Click on apply",
            trigger: ".o_we_apply_link",
            run: "click",
        },
        {
            content: "Check if a document link is created",
            trigger: ":iframe #wrap .s_banner a[href^='/web/content']",
        },
        unpatchStep,
        // TODO: reimplement these steps if the auto-download option comes back
        // {
        //     content: "Check if by default the option auto-download is enabled",
        //     trigger: ":iframe #wrap .s_banner .oe_edited_link[href$='download=true']",
        // },
        // {
        //     content: "Deactivate direct download",
        //     trigger: ".o_switch > we-checkbox[name='direct_download']",
        //     run: "click",
        // },
        // {
        //     content: "Check if auto-download is disabled",
        //     trigger: ":iframe #wrap .s_banner .oe_edited_link:not([href$='download=true'])",
        // },
    ]
);
