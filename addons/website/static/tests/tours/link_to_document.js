import { registry } from "@web/core/registry";
import { insertSnippet, openLinkPopup, waitForEditMode } from "@website/js/tours/tour_utils";
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
                // hardcoded id for test_03_link_to_document
                return [{ id: 437296, name: "file.txt", public: true, checksum: "123" }];
            },
        });
    },
};
const unpatchStep = {
    content: "Unpatch upload service",
    trigger: "body",
    run: () => unpatch(),
};

const saveLinkPopup = () => [
    {
        content: "Save the link by clicking on Apply button",
        trigger: ".o-we-linkpopover .o_we_apply_link",
        run: "click",
    },
];

/**
 * The purpose of this tour is to check the Linktools to create a link to an
 * uploaded document.
 */
registry.category("web_tour.tours").add("test_link_to_document", {
    steps: () => [
        waitForEditMode,
        ...insertSnippet({
            name: "Banner",
            id: "s_banner",
            groupName: "Intro",
        }),
        patchStep,
        ...openLinkPopup({
            trigger: `:iframe #wrap .s_banner a:nth-child(1)`,
            label: "Contact Us",
            url: "/contactus",
            edit: true,
        }),
        {
            trigger: ".o-we-linkpopover .o_we_href_input_link",
            run: "edit ",
        },
        {
            content: "Click on link to an uploaded document",
            trigger: ".o-we-linkpopover div.o-autocomplete ~ span > button",
            run: "click",
        },
        ...saveLinkPopup(),
        {
            content: "Check if a document link is created",
            trigger: ":iframe #wrap .s_banner a:nth-child(1)[href^='/web/content']",
        },
        {
            content: "Check if by default the option auto-download is enabled",
            trigger: ":iframe #wrap .s_banner a:nth-child(1)[href$='download=true']",
        },
        unpatchStep,
        {
            content: `Click on outside to select something else`,
            trigger: `:iframe #wrap .s_banner p:nth-child(2)`,
            async run() {
                const el = this.anchor;
                const sel = el.ownerDocument.getSelection();
                sel.collapse(el.childNodes[1], 1);
                el.focus();
            },
        },
        {
            content: "Wait for link popover to close",
            trigger: "body:not(:has(.o-we-linkpopover))",
        },
        ...openLinkPopup({
            trigger: `:iframe #wrap .s_banner a:nth-child(1)`,
            label: "sample.txt",
            url: "/web/content/437296?unique=123&download=true",
            edit: true,
        }),
        {
            content: "Deactivate direct download",
            trigger: ".o-we-linkpopover .direct-download-option > input",
            run: "click",
        },
        ...saveLinkPopup(),
        {
            content: "Check if auto-download is disabled",
            trigger: ":iframe #wrap .s_banner a:nth-child(1):not([href$='download=true'])",
        },
    ],
});
