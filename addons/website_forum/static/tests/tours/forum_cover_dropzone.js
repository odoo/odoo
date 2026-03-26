import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "forum_cover_dropzone",
    {
        url: "/forum/help-1",
        edition: true,
    },
    () => [
        // Add a snippet on click.
        {
            content: "Click on the Text snippet group.",
            trigger:
                '.o_block_tab:not(.o_we_ongoing_insertion) #snippet_groups .o_snippet[name="Text"].o_draggable .o_snippet_thumbnail_area',
            run: "click",
        },
        {
            content: "Select the 'Title' snippet in the dialog.",
            trigger: ':iframe .o_snippet_preview_wrap[data-snippet-id="s_title"]:not(.d-none)',
            run: "click",
        },
        {
            content: "Check that the 'Title' snippet was inserted in the forum cover.",
            trigger: ":iframe .s_cover .s_title",
        },
        // Add a snippet with drag and drop.
        {
            content: "Drag the Form snippet group into the forum cover.",
            trigger:
                '.o_block_tab:not(.o_we_ongoing_insertion) #snippet_groups .o_snippet[name="Contact & Forms"].o_draggable .o_snippet_thumbnail_area',
            run: "drag_and_drop :iframe #wrapwrap .s_cover .oe_drop_zone:last",
        },
        {
            content: "Select the 'Title - Form' snippet in the dialog",
            trigger: ':iframe .o_snippet_preview_wrap[data-snippet-id="s_title_form"]:not(.d-none)',
            run: "click",
        },
        {
            content: "Check that the 'Title - Form' snippet was inserted in the forum cover.",
            trigger: ":iframe .s_cover .s_title_form",
        },
        // Check that it is impossible to drop "Embed Code" (= sanitized area).
        {
            content: "Open the Content snippet group.",
            trigger:
                '.o_block_tab:not(.o_we_ongoing_insertion) #snippet_groups .o_snippet[name="Content"].o_draggable .o_snippet_thumbnail_area',
            run: "drag_and_drop :iframe #wrapwrap .s_cover .oe_drop_zone:last",
        },
        {
            content: "Type 'embed' in the searchbar to find for the embed_code snippet",
            trigger: '.o_add_snippet_dialog input[type="search"]',
            run: "edit embed_code",
        },
        {
            content: "Check that the search returns no results.",
            trigger: '.o_add_snippet_dialog input[type="search"]',
            run() {
                const previewDocument =
                    document.querySelector(".o_add_snippet_iframe").contentDocument;
                if (previewDocument.querySelector(".o_snippet_preview_wrap")) {
                    throw new Error("Expected no snippet results in the add snippet dialog.");
                }
            },
        },
    ]
);
