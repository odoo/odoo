import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    insertSnippet,
    goBackToBlocks,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const scrollToHeading = function (position) {
    return {
        content: `Scroll to h2 number ${position}`,
        trigger: `:iframe .s_table_of_content h2:eq(${position})`,
        run: function () {
            this.anchor.scrollIntoView({ behavior: "smooth", block: "center" });
        },
    };
};
const checkTOCNavBar = function (tocPosition, activeHeaderPosition) {
    return {
        content: `Check that the header ${activeHeaderPosition} is active for TOC ${tocPosition}`,
        trigger: `:iframe .s_table_of_content:eq(${tocPosition}) .table_of_content_link:eq(${activeHeaderPosition}).active `,
    };
};

registerWebsitePreviewTour(
    "snippet_table_of_content",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_table_of_content", name: "Table of Content", groupName: "Text" }),
        {
            content: "Drag the Text snippet group and drop it.",
            trigger:
                ".o-snippets-menu .o_block_tab:not(.o_we_ongoing_insertion) .o_snippet[name='Text'] .o_snippet_thumbnail",
            run: "drag_and_drop :iframe #wrap",
        },
        {
            content: "Click on the s_table_of_content snippet.",
            trigger: ':iframe .o_add_snippets_preview [data-snippet="s_table_of_content"]',
            run: "click",
        },
        // To make sure that the public widgets of the two previous ones started.
        ...insertSnippet({ id: "s_banner", name: "Banner", groupName: "Intro" }),
        {
            content: "Drag the Intro snippet group and drop it.",
            trigger:
                ".o-snippets-menu .o_block_tab:not(.o_we_ongoing_insertion) .o_snippet[name='Intro'] .o_snippet_thumbnail",
            run: "drag_and_drop :iframe #wrap",
        },
        {
            content: "Click on the s_banner snippet.",
            trigger: ':iframe .o_add_snippets_preview [data-snippet="s_banner"]',
            run: "click",
        },
        ...clickOnSave(),
        checkTOCNavBar(0, 0),
        checkTOCNavBar(1, 0),
        scrollToHeading(1),
        checkTOCNavBar(0, 1),
        checkTOCNavBar(1, 0),
        scrollToHeading(2),
        checkTOCNavBar(1, 0),
        scrollToHeading(3),
        checkTOCNavBar(1, 0),
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Click on the first TOC's title",
            trigger: ":iframe .s_table_of_content:eq(0) h2",
            run: "click",
        },
        {
            content: "Hide the first TOC on mobile",
            trigger: '[data-action-param="no_mobile"]',
            run: "click",
        },
        // Go back to blocks tabs to avoid changing the first ToC options
        goBackToBlocks(),
        {
            content: "Click on the second TOC's title",
            trigger: ":iframe .s_table_of_content:eq(1) h2",
            run: "click",
        },
        {
            content: "Hide the second TOC on desktop",
            trigger: '[data-action-param="no_desktop"]',
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Check that we have the good TOC on desktop",
            trigger: ":iframe .s_table_of_content.o_snippet_mobile_invisible",
        },
        {
            content: "The mobile TOC should not be visible on desktop",
            trigger: ":iframe .s_table_of_content.o_snippet_desktop_invisible:not(:visible)",
        },
        {
            content: "Toggle the mobile view",
            trigger: ".o_mobile_preview > a",
            run: "click",
        },
        {
            content: "Check that we have the good TOC on mobile",
            trigger: ":iframe .s_table_of_content.o_snippet_desktop_invisible",
        },
        {
            content: "The desktop TOC should not be visible on mobile",
            trigger: ":iframe .s_table_of_content.o_snippet_mobile_invisible:not(:visible)",
        },
    ]
);
