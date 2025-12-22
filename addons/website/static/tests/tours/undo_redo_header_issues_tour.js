import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

const badgePositionSelector = ":iframe #wrapwrap header .navbar .navbar-nav .s_text_block";

const clickUndoRedo = (action, waitSelector) => {
    const btnSelector =
        action === "undo"
            ? ".o_we_website_top_actions .fa-undo"
            : ".o_we_website_top_actions .fa-repeat";
    return [
        {
            content: `Click ${action} button`,
            trigger: btnSelector,
            run: "click",
        },
        {
            content: `Wait until ${action} action is applied`,
            trigger: waitSelector,
        },
    ];
};

const checkNoBadge = () => ({
    content: "Check that badge is not present",
    trigger: ":iframe #wrapwrap header .navbar:not(:has(.s_badge))",
});

registerWebsitePreviewTour(
    "undo_redo_header_oriented_issue",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_three_columns", name: "Columns", groupName: "Columns" }),
        ...insertSnippet({ id: "s_carousel", name: "Carousel", groupName: "Intro" }),
        ...insertSnippet({ id: "s_text_image", name: "Text - Image", groupName: "Content" }),
        ...insertSnippet({ id: "s_media_list", name: "Media List", groupName: "Content" }),
        {
            trigger: ":iframe .s_three_columns",
            run() {
                this.anchor.scrollIntoView();
            },
        },
        {
            content: "Drag the badge building block and drop it at the bottom of the page header.",
            trigger: `#oe_snippets .oe_snippet[name="Badge"].o_we_draggable .oe_snippet_thumbnail:not(.o_we_ongoing_insertion)`,
            run: `drag_and_drop ${badgePositionSelector}`,
        },
        {
            content: "Wait for badge to be inserted",
            trigger: `${badgePositionSelector} .s_badge.o_draggable`,
        },
        ...clickUndoRedo("undo", ":iframe #wrapwrap > header :not(.s_badge)"),
        ...clickUndoRedo("undo", ":iframe :not(.s_media_list)"),
        checkNoBadge(),
        ...clickUndoRedo("undo", ":iframe :not(.s_text_image)"),
        ...clickUndoRedo("undo", ":iframe :not(.s_carousel)"),
        checkNoBadge(),
        ...clickUndoRedo("redo", ":iframe .s_carousel"),
        ...clickUndoRedo("redo", ":iframe .s_text_image"),
        ...clickUndoRedo("redo", ":iframe .s_media_list"),
        {
            content: "Check that Contact Us button is not duplicated after 3 redos.",
            trigger: `:iframe #wrapwrap header .navbar .navbar-nav :has(.btn.btn-primary.btn_cta):not(:has(.btn.btn-primary.btn_cta:nth-of-type(2)))`,
        },
    ]
);
