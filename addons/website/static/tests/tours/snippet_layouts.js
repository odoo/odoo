import {
    insertSnippet,
    registerWebsitePreviewTour,
    clickOnSnippet,
    changeOption,
    goBackToBlocks,
} from "@website/js/tours/tour_utils";

const snippets = [
    { id: "s_key_images", name: "Key Images" },
    { id: "s_cards_soft", name: "Cards Soft" },
    { id: "s_cards_grid", name: "Cards Grid" },
];

function getSnippetSteps(snippet) {
    const snippetRow = `:iframe .${snippet.id} .row`;
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
        changeOption(`${snippet.name}`, "[data-action-param='align-items-start']"),
        {
            content: `Check that the vertical alignment is set to center for ${snippet.name}`,
            trigger: `${snippetRow}.align-items-start`,
        },
        changeOption(`${snippet.name}`, "[data-action-param='align-items-center']"),
        {
            content: `Check that the vertical alignment is set to start for ${snippet.name}`,
            trigger: `${snippetRow}.align-items-center`,
        },
        changeOption(`${snippet.name}`, "[data-action-param='align-items-end']"),
        {
            content: `Check that the vertical alignment is set to end for ${snippet.name}`,
            trigger: `${snippetRow}.align-items-end`,
        },
        goBackToBlocks(),
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
