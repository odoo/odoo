import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_add_snippet_dialog",
    {
        edition: true,
        url: "/",
    },
    () => [
        {
            content: "Click on any snippet to open the 'Insert Snippet' dialog.",
            trigger: ".o_snippets_container_body div.o_snippet button",
            run: "click",
        },
        {
            content: "Ensure that snippets are displayed.",
            trigger: ":iframe .o_add_snippets_preview [data-snippet-id]",
        },
        {
            content:
                "Enter a search term that does not match any snippet to test empty results behavior.",
            trigger: ".modal input",
            run: "edit NoSnippetsAvailable",
        },
        {
            content: "Verify that the appropriate message is displayed when no snippets are found.",
            trigger:
                "p:contains('Oops! No snippets found.'), p:contains('Take a look at the search bar, there might be a small typo!')",
        },
    ]
);
