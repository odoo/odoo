import {
    insertSnippet,
    registerWebsitePreviewTour,
    clickOnSnippet,
} from "@website/js/tours/tour_utils";

const columnCountOptSelector =
    ".snippet-option-layout_column we-select[data-name='column_count_opt']";
const snippetRows = {
    s_cards_soft: ":iframe .s_cards_soft .row",
    s_cards_grid: ":iframe .s_cards_grid .row",
    s_key_benefits: ":iframe .s_key_benefits .row",
    s_key_images: ":iframe .s_key_images .row",
};
const verticalAlignmentOptSelectors = {
    s_cards_soft:
        ".o_we_customize_panel we-customizeblock-options:has(we-title:contains('Cards Soft'))",
    s_cards_grid:
        ".o_we_customize_panel we-customizeblock-options:has(we-title:contains('Cards Grid'))",
    s_key_benefits:
        ".o_we_customize_panel we-customizeblock-options:has(we-title:contains('Key Benefits'))",
    s_key_images:
        ".o_we_customize_panel we-customizeblock-options:has(we-title:contains('Key Images'))",
};

function generateTourSteps(snippets) {
    let steps = [];
    snippets.forEach(({ id, name }) => {
        const snippetRow = snippetRows[id];
        const verticalAlignmentOptSelector = verticalAlignmentOptSelectors[id];

        steps = steps.concat([
            // Test column count for the snippet
            ...insertSnippet({
                id: id,
                name: name,
                groupName: "Columns",
            }),
            ...clickOnSnippet({
                id: id,
                name: name,
            }),
            {
                content: "Open the columns count select",
                trigger: columnCountOptSelector,
                run: "click",
            },
            {
                content: `Set 3 columns on desktop for ${name}`,
                trigger: `${columnCountOptSelector} we-button[data-select-count='3']`,
                run: "click",
            },
            {
                content: `Check that there are now 3 items on 3 columns for ${name}`,
                trigger: `${snippetRow}:has(.col-lg-4:nth-child(3))`,
            },
            {
                content: "Open the columns count select",
                trigger: columnCountOptSelector,
                run: "click",
            },
            {
                content: `Set 1 column on desktop for ${name}`,
                trigger: `${columnCountOptSelector} we-button[data-select-count='1']`,
                run: "click",
            },
            {
                content: `Check that there are still 3 items in the row for ${name}`,
                trigger: `${snippetRow} > :nth-child(3)`,
            },
            // Test vertical alignment for the snippet
            {
                content: "Open the vertical alignment options",
                trigger: `${verticalAlignmentOptSelector} we-title:contains('Vert. Alignment')`,
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
    "snippet_layouts_test",
    {
        url: "/",
        edition: true,
    },
    () => generateTourSteps(snippets)
);
