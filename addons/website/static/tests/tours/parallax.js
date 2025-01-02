import {
    changeOption,
    clickOnEditAndWaitEditMode,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const coverSnippet = {id: "s_cover", name: "Cover", groupName: "Intro"};

registerWebsitePreviewTour("test_parallax", {
    url: "/",
    edition: true,
    checkDelay: 500,
}, () => [
    ...insertSnippet(coverSnippet),
    ...clickOnSnippet(coverSnippet),
    changeOption("BackgroundOptimize", "we-toggler"),
    changeOption("BackgroundOptimize", 'we-button[data-gl-filter="blur"]'),
{
    content: "Check that the Cover snippet has the Blur filter on its background image",
    trigger: ":iframe .s_cover span[data-gl-filter='blur']",
},
    changeOption("Parallax", "we-toggler"),
    changeOption("Parallax", 'we-button[data-select-data-attribute="0"]'),
{
    content: "Check that the data related to the filter have been transferred to the new target",
    trigger: ":iframe .s_cover[data-gl-filter='blur']",
},
{
    content: "Check that the 'o_modified_image_to_save' class has been transferred to the new target",
    trigger: ":iframe .s_cover.o_modified_image_to_save",
},
    changeOption("Parallax", "we-toggler"),
    changeOption("Parallax", 'we-button[data-select-data-attribute="1"]'),
{
    content: "Check that the 'o_modified_image_to_save' class has been deleted from the old target",
    trigger: ":iframe .s_cover:not(.o_modified_image_to_save)",
},
{
    content: "Check that the 'o_modified_image_to_save' class has been transferred to the new target",
    trigger: ":iframe span.s_parallax_bg.o_modified_image_to_save",
},
{
    content: "Check that the data related to the filter have been transferred to the new target",
    trigger: ":iframe span.s_parallax_bg[data-gl-filter='blur']",
},
    changeOption("Parallax", "we-toggler"),
    changeOption("Parallax", 'we-button[data-select-data-attribute="1.5"]'),
{
    content: "Check that the option was correctly applied",
    trigger: ':iframe span.s_parallax_bg[style*=top][style*=bottom][style*=transform]',
},
    ...clickOnSave(),
    ...clickOnEditAndWaitEditMode(),
{
    content: "The parallax should not add o_dirty when entering edit mode",
    trigger: ':iframe #wrap:not(.o_dirty)',
},
]);
