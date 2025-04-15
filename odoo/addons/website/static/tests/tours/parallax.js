/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

const coverSnippet = {id: "s_cover", name: "Cover"};

wTourUtils.registerWebsitePreviewTour("test_parallax", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop(coverSnippet),
    wTourUtils.clickOnSnippet(coverSnippet),
    wTourUtils.changeOption("BackgroundOptimize", "we-toggler"),
    wTourUtils.changeOption("BackgroundOptimize", 'we-button[data-gl-filter="blur"]'),
{
    content: "Check that the Cover snippet has the Blur filter on its background image",
    trigger: "iframe .s_cover span[data-gl-filter='blur']",
    isCheck: true,
},
    wTourUtils.changeOption("Parallax", "we-toggler"),
    wTourUtils.changeOption("Parallax", 'we-button[data-select-data-attribute="0"]'),
{
    content: "Check that the data related to the filter have been transferred to the new target",
    trigger: "iframe .s_cover[data-gl-filter='blur']",
    isCheck: true,
},
{
    content: "Check that the 'o_modified_image_to_save' class has been transferred to the new target",
    trigger: "iframe .s_cover.o_modified_image_to_save",
    isCheck: true,
},
    wTourUtils.changeOption("Parallax", "we-toggler"),
    wTourUtils.changeOption("Parallax", 'we-button[data-select-data-attribute="1"]'),
{
    content: "Check that the 'o_modified_image_to_save' class has been deleted from the old target",
    trigger: "iframe .s_cover:not(.o_modified_image_to_save)",
    isCheck: true,
},
{
    content: "Check that the 'o_modified_image_to_save' class has been transferred to the new target",
    trigger: "iframe span.s_parallax_bg.o_modified_image_to_save",
    isCheck: true,
},
{
    content: "Check that the data related to the filter have been transferred to the new target",
    trigger: "iframe span.s_parallax_bg[data-gl-filter='blur']",
    isCheck: true,
},
    wTourUtils.changeOption("Parallax", "we-toggler"),
    wTourUtils.changeOption("Parallax", 'we-button[data-select-data-attribute="1.5"]'),
{
    content: "Check that the option was correctly applied",
    trigger: 'iframe span.s_parallax_bg[style*=top][style*=bottom][style*=transform]',
    run: () => {}, //it's a check
},
    ...wTourUtils.clickOnSave(),
    ...wTourUtils.clickOnEditAndWaitEditMode(),
{
    content: "The parallax should not add o_dirty when entering edit mode",
    trigger: 'iframe #wrap:not(.o_dirty)',
    run: () => {}, //it's a check
},
]);
