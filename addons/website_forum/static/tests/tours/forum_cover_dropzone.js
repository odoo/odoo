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
                '#oe_snippets .oe_snippet[name="Text"].o_we_draggable .oe_snippet_thumbnail:not(.o_we_ongoing_insertion)',
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
            trigger: `#oe_snippets .oe_snippet[name="Contact & Forms"].o_we_draggable .oe_snippet_thumbnail:not(.o_we_ongoing_insertion)`,
            run: "drag_and_drop :iframe #wrapwrap .s_cover",
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
                '#oe_snippets .oe_snippet[name="Content"].o_we_draggable .oe_snippet_thumbnail:not(.o_we_ongoing_insertion)',
            run: "click",
        },
        {
            content: "Type 'embed' in the searchbar to find for the embed_code snippet",
            trigger: '.o_add_snippet_dialog input[type="search"]',
            run: "edit embed",
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
