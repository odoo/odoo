import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_multi_edition",
    {
        url: "/",
        edition: true,
    },
    () => [
        {
            content: "Check the current page has not the elements that will be added",
            trigger: ":iframe body:not(:has(.s_text_image)):not(:has(.s_hr))",
        },
        // Edit the main element of the page
        ...insertSnippet({
            id: "s_text_image",
            name: "Text - Image",
            groupName: "Content",
        }),
        // Edit another part in the page, like the footer
        {
            trigger: ".o-website-builder_sidebar.o_builder_sidebar_open .o_snippet",
        },
        {
            trigger: `.o-snippets-menu .o_block_tab:not(.o_we_ongoing_insertion) .o_snippet[name="Separator"].o_draggable .o_snippet_thumbnail`,
            content: "Drag the Separator building block and drop it at the bottom of the page.",
            run: "drag_and_drop :iframe .oe_drop_zone:last",
        },
        ...clickOnSave(),
        {
            content: "Check that the main element of the page was properly saved",
            trigger: ":iframe main .s_text_image",
        },
        {
            content: "Check that the footer was properly saved",
            trigger: ":iframe footer .s_hr",
        },
    ]
);
