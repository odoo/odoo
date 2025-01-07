import {
    insertSnippet,
    registerWebsitePreviewTour,
    clickOnSnippet,
    changeOption,
} from "@website/js/tours/tour_utils";

const snippetRow = `:iframe .s_key_images .row`;
const verticalAlignmentOptSelector = `.o_we_customize_panel we-customizeblock-options:has(we-title:contains("Key Images")`;

registerWebsitePreviewTour(
    "snippet_layout",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_key_images",
            name: "Key Images",
            groupName: "Columns",
        }),
        ...clickOnSnippet({
            id: "s_key_images",
            name: "Key Images",
        }),
        // Test vertical alignment for the snippet
        {
            content: "Open the vertical alignment options",
            trigger: `${verticalAlignmentOptSelector} we-title:contains('Vertical Alignment')`,
            run: "click",
        },
        changeOption("vAlignment", 'we-button[data-select-class="align-items-center"]'),
        {
            content: `Check that the vertical alignment is set to center for Key Images`,
            trigger: `${snippetRow}.align-items-center`,
        },
        changeOption("vAlignment", 'we-button[data-select-class="align-items-start"]'),
        {
            content: `Check that the vertical alignment is set to start for Key Images`,
            trigger: `${snippetRow}.align-items-start`,
        },
        changeOption("vAlignment", 'we-button[data-select-class="align-items-end"]'),
        {
            content: `Check that the vertical alignment is set to end for Key Images`,
            trigger: `${snippetRow}.align-items-end`,
        },
        {
            content: "Go back to blocks",
            trigger: ".o_we_add_snippet_btn",
            run: "click",
        },
    ]
);
