import {
    insertSnippet,
    registerWebsitePreviewTour,
    clickOnSnippet,
    changeOption,
} from "@website/js/tours/tour_utils";

const snippets = [
    { id: "s_key_images", name: "Key Images" },
    { id: "s_cards_soft", name: "Cards Soft" },
    { id: "s_cards_grid", name: "Cards Grid" },
];

function getSnippetSteps(snippet) {
    const snippetRow = `:iframe .${snippet.id} .row`;
    const verticalAlignmentOptSelector = `.o_we_customize_panel we-customizeblock-options:has(we-title:contains("${snippet.name}"))`;

    return [
        ...insertSnippet({
            id: snippet.id,
            name: snippet.name,
            groupName: "Columns",
        }),
        ...clickOnSnippet({
            id: snippet.id,
            name: snippet.name,
        }),
        {
            content: "Open the vertical alignment options",
            trigger: `${verticalAlignmentOptSelector} we-title:contains('Vertical Alignment')`,
            run: "click",
        },
        changeOption("vAlignment", 'we-button[data-select-class="align-items-center"]'),
        {
            content: `Check that the vertical alignment is set to center for ${snippet.name}`,
            trigger: `${snippetRow}.align-items-center`,
        },
        changeOption("vAlignment", 'we-button[data-select-class="align-items-start"]'),
        {
            content: `Check that the vertical alignment is set to start for ${snippet.name}`,
            trigger: `${snippetRow}.align-items-start`,
        },
        changeOption("vAlignment", 'we-button[data-select-class="align-items-end"]'),
        {
            content: `Check that the vertical alignment is set to end for ${snippet.name}`,
            trigger: `${snippetRow}.align-items-end`,
        },
        {
            content: "Go back to blocks",
            trigger: ".o_we_add_snippet_btn",
            run: "click",
        },
    ];
}

registerWebsitePreviewTour(
    "snippet_layout",
    {
        url: "/",
        edition: true,
    },
    () => snippets.flatMap(getSnippetSteps)
);
