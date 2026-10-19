import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_add_snippet_dialog",
    {
        edition: true,
    },
    () => [
        {
            content: "Click on any snippet to open the 'Insert Snippet' dialog.",
            trigger: ".o_snippets_container_body div.o_snippet button",
            run: "click",
        },
        {
            content: "Ensure that snippets are displayed with the website fonts.",
            trigger: ":iframe .o_add_snippets_preview [data-snippet-id]",
            run() {
                const websiteIframeEl = document.querySelector(
                    ".o_iframe_container iframe:not(.o_ignore_in_tour)"
                );
                const fontLinkEls = websiteIframeEl.contentDocument.head.querySelectorAll(
                    'link[rel="stylesheet"]:not([type])'
                );
                const previewHrefs = new Set(
                    [
                        ...this.anchor.ownerDocument.head.querySelectorAll(
                            'link[rel="stylesheet"]'
                        ),
                    ].map((linkEl) => linkEl.getAttribute("href"))
                );
                for (const fontLinkEl of fontLinkEls) {
                    if (!previewHrefs.has(fontLinkEl.getAttribute("href"))) {
                        throw new Error(
                            "A website font stylesheet is missing from the snippet dialog."
                        );
                    }
                }
            },
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
