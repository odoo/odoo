import {
    insertSnippet,
    clickOnSave,
    clickOnEditAndWaitEditMode,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

function waitEndOfPopupAnimation({ hidden = false } = {}) {
    return {
        content: "Wait for end of animation showing popup (hiding/showing disabled during it)",
        trigger: `:iframe #wrap .s_popup .modal${hidden ? ":not(:visible)" : ""}`,
        run: async ({ anchor }) => {
            await new Promise((resolve) =>
                window.Modal.getOrCreateInstance(anchor)._queueCallback(resolve, anchor)
            );
        },
    };
}

registerWebsitePreviewTour(
    "snippet_visibility_option",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_popup",
            name: "Popup",
            groupName: "Content",
        }),
        {
            content: "Click on the column within the popup snippet.",
            trigger: ":iframe #wrap .s_popup .o_cc1",
            run: "click",
        },
        {
            content: "Click the 'No Desktop' visibility option.",
            trigger: "[data-container-title='Column'] [data-action-param='no_desktop']",
            run: "click",
        },
        {
            content: "Check the column is hidden",
            trigger: ":iframe #wrap .s_popup .o_cc1:not(:visible)",
        },
        {
            content: "Click on the banner within the popup snippet.",
            trigger: ":iframe #wrap .s_popup .s_banner",
            run: "click",
        },
        {
            content: "Click the 'No Desktop' visibility option.",
            trigger: "[data-container-title='Block'] [data-action-param='no_desktop']",
            run: "click",
        },
        {
            content: "Check the banner is hidden",
            trigger: ":iframe #wrap .s_popup .s_banner:not(:visible)",
        },
        waitEndOfPopupAnimation(),
        {
            content: "Click on the popup entry to hide it",
            trigger: ".o_we_invisible_root_parent > i.fa-eye",
            run: "click",
        },
        {
            content: "Check the popup is hidden",
            trigger: ":iframe #wrap .s_popup .modal:not(:visible)",
        },
        waitEndOfPopupAnimation({ hidden: true }),
        {
            content: "Click on the popup entry in the list of invisible elements.",
            trigger: ".o_we_invisible_root_parent > i.fa-eye-slash",
            run: "click",
        },
        {
            content: "Check the popup is visible",
            trigger: ":iframe #wrap .s_popup .modal:visible",
        },
        {
            content: "Check that only the banner is marked as invisible",
            trigger: "li > .o_we_invisible_entry i.fa-eye-slash",
        },
        {
            content: "And the column entry does not appear in the panel.",
            trigger: "body:not(:has(li li .o_we_invisible_entry))",
        },
        ...clickOnSave(),
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Check the popup is hidden",
            trigger: ":iframe #wrap .s_popup .modal:not(:visible)",
        },
        {
            content: "Check that the popup entry is displayed and marked as invisible",
            trigger: ".o_we_invisible_root_parent > i.fa-eye-slash",
        },
        {
            content: "Check that the entry for the child of popup is not displayed",
            trigger: "body:not(:has(li .o_we_invisible_entry))",
        },
        waitEndOfPopupAnimation({ hidden: true }),
        {
            content: "Click on the popup entry to show it.",
            trigger: ".o_we_invisible_root_parent > i.fa-eye-slash",
            run: "click",
        },
        {
            content: "Check the popup is visible",
            trigger: ":iframe #wrap .s_popup .modal:visible",
        },
        {
            content: "Click on the banner entry to show it.",
            trigger: "li > .o_we_invisible_entry > i.fa-eye-slash",
            run: "click",
        },
        {
            content: "Check that the popup entry is displayed and marked as visible",
            trigger: ".o_we_invisible_root_parent > i.fa-eye",
        },
        {
            content: "Check that the banner entry is displayed and marked as visible",
            trigger: "li .o_we_invisible_entry > i.fa-eye",
        },
        {
            content: "Check that the column entry is displayed and marked as invisible",
            trigger: "li li .o_we_invisible_entry > i.fa-eye-slash",
        },
        waitEndOfPopupAnimation(),
        {
            content: "Click on the popup entry to hide it.",
            trigger: ".o_we_invisible_root_parent > i.fa-eye",
            run: "click",
        },
        {
            content: "Check the popup is hidden",
            trigger: ":iframe #wrap .s_popup .modal:not(:visible)",
        },
        {
            content: "Check that the popup entry is displayed and marked as invisible",
            trigger: ".o_we_invisible_root_parent > i.fa-eye-slash",
        },
        {
            content: "Check that the entry for the child of popup is not displayed",
            trigger: "body:not(:has(li .o_we_invisible_entry))",
        },
        waitEndOfPopupAnimation({ hidden: true }),
        {
            content: "Click on the popup entry to show it.",
            trigger: ".o_we_invisible_root_parent > i.fa-eye-slash",
            run: "click",
        },
        {
            content: "Check the popup is visible",
            trigger: ":iframe #wrap .s_popup .modal:visible",
        },
        {
            content: "Check that the popup entry is displayed and marked as visible",
            trigger: ".o_we_invisible_root_parent i.fa-eye",
        },
        {
            content: "Check that the banner entry is displayed and marked as visible",
            trigger: "li .o_we_invisible_entry i.fa-eye",
        },
        {
            content: "Check that the column entry is displayed and marked as invisible",
            trigger: "li li .o_we_invisible_entry i.fa-eye-slash",
        },
    ]
);
