import {
    insertSnippet,
    clickOnSave,
    clickOnEditAndWaitEditMode,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

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
            content: "Click on the popup snippet to hide",
            trigger: ".o_we_invisible_root_parent",
            run: "click",
        },
        {
            content: "Click on the popup snippet in the list of invisible elements.",
            trigger: ".o_we_invisible_root_parent",
            run: "click",
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
            content: "Check that only the popup entry is displayed...",
            trigger: ".o_we_invisible_root_parent > i.fa-eye-slash",
        },
        {
            content: "...and that it is invisible",
            trigger: "body:not(:has(li .o_we_invisible_entry))",
        },
        {
            content: "Click on the popup entry to show it.",
            trigger: ".o_we_invisible_root_parent",
            run: "click",
        },
        {
            content: "Click on the banner entry to show it.",
            trigger: "li > .o_we_invisible_entry",
            run: "click",
        },
        {
            trigger: ".o_we_invisible_root_parent i.fa-eye",
        },
        {
            trigger: "li .o_we_invisible_entry i.fa-eye",
        },
        {
            trigger: "li li .o_we_invisible_entry i.fa-eye-slash",
        },
        {
            content: "Click on the popup entry to hide it.",
            trigger: ".o_we_invisible_root_parent",
            run: "click",
        },
        {
            trigger: "li .o_we_invisible_entry",
        },
        {
            trigger: ".o_we_invisible_root_parent > i.fa-eye-slash",
        },
        {
            content: "Click on the popup entry to show it.",
            trigger: ".o_we_invisible_root_parent",
            run: "click",
        },
        {
            trigger: ".o_we_invisible_root_parent i.fa-eye",
        },
        {
            trigger: "li .o_we_invisible_entry i.fa-eye",
        },
        {
            trigger: "li li .o_we_invisible_entry i.fa-eye-slash",
        },
    ]
);
