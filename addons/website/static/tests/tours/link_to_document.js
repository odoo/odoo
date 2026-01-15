import {
    insertSnippet,
    openLinkPopup,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";
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

const editLinkPopup = () => [
    ...openLinkPopup(`:iframe #wrap .s_banner a:nth-child(1)`, "Start Now", 1, true),
    {
        trigger: ".o-we-linkpopover .o_we_edit_link",
        run: "click",
    },
];

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
        patchStep,
        ...editLinkPopup(),
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
        ...editLinkPopup(),
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
    ]
);
