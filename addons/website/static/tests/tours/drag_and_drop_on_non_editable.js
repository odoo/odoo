import {
    insertSnippet,
    goBackToBlocks,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "test_drag_and_drop_on_non_editable",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_company_team",
            name: "Team",
            groupName: "People",
        }),
        {
            content: "Click on an editable media in non editable env.",
            trigger: ":iframe .s_company_team .o_not_editable > .o_editable_media",
            run: "click",
        },
        {
            content: "Verify that the Replace options is in the editor.",
            trigger: "[data-label='Media'] button[data-action-id='replaceMedia']",
        },
        goBackToBlocks(),
        {
            trigger: ".o_builder_sidebar_open .o_snippet",
        },
        {
            content:
                "Drag and drop the Text Highlight building block next to the Team block media.",
            trigger:
                ".o_block_tab:not(.o_we_ongoing_insertion) .o_snippet[name='Text Highlight'].o_draggable .o_snippet_thumbnail",
            run: "drag_and_drop :iframe .s_company_team .o_not_editable > .o_editable_media",
        },
        {
            content:
                "Verify that the Text Highlight building block isn't in a non editable element.",
            trigger: ":iframe .s_company_team :not(.o_not_editable) > .s_text_highlight",
        },
    ]
);
