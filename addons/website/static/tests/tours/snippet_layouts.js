import {
    insertSnippet,
    registerWebsitePreviewTour,
    clickOnSnippet,
} from "@website/js/tours/tour_utils";

function generateTourSteps(snippets) {
    let steps = [];
    snippets.forEach(({ id, name }) => {
        const snippetRow = `:iframe .${id} .row`;
        const verticalAlignmentOptSelector = `.o_we_customize_panel we-customizeblock-options:has(we-title:contains(${name}))`;

        steps = steps.concat([
            // Insert the snippet
            ...insertSnippet({
                id: id,
                name: name,
                groupName: "Columns",
            }),
            ...clickOnSnippet({
                id: id,
                name: name,
            }),
            // Test vertical alignment for the snippet
            {
                content: "Open the vertical alignment options",
                trigger: `${verticalAlignmentOptSelector} we-title:contains('Vertical Alignment')`,
                run: "click",
            },
            {
                content: "Set vertical alignment to center",
                trigger: `${verticalAlignmentOptSelector} we-button[data-select-class='align-items-center']`,
                run: "click",
            },
            {
                content: `Check that the vertical alignment is set to center for ${name}`,
                trigger: `${snippetRow}.align-items-center`,
            },
            {
                content: "Set vertical alignment to start",
                trigger: `${verticalAlignmentOptSelector} we-button[data-select-class='align-items-start']`,
                run: "click",
            },
            {
                content: `Check that the vertical alignment is set to start for ${name}`,
                trigger: `${snippetRow}.align-items-start`,
            },
            {
                content: "Set vertical alignment to end",
                trigger: `${verticalAlignmentOptSelector} we-button[data-select-class='align-items-end']`,
                run: "click",
            },
            {
                content: `Check that the vertical alignment is set to end for ${name}`,
                trigger: `${snippetRow}.align-items-end`,
            },
            {
                content: "Go back to blocks",
                trigger: ".o_we_add_snippet_btn",
                run: "click",
            },
        ]);
    });
    return steps;
}

const snippets = [
    { id: "s_cards_soft", name: "Cards Soft" },
    { id: "s_cards_grid", name: "Cards Grid" },
    { id: "s_key_benefits", name: "Key Benefits" },
    { id: "s_key_images", name: "Key Images" },
];

registerWebsitePreviewTour(
    "snippet_layout",
    {
        url: "/",
        edition: true,
    },
    () => generateTourSteps(snippets)
);
