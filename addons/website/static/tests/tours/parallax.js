odoo.define("website.tour.parallax", function (require) {
"use strict";

const wTourUtils = require("website.tour_utils");

const coverSnippet = {id: "s_cover", name: "Cover"};

wTourUtils.registerWebsitePreviewTour("test_parallax", {
    test: true,
    url: "/",
    edition: true,
}, [
    wTourUtils.dragNDrop(coverSnippet),
    wTourUtils.clickOnSnippet(coverSnippet),
    wTourUtils.changeOption("BackgroundOptimize", "we-toggler"),
    wTourUtils.changeOption("BackgroundOptimize", 'we-button[data-gl-filter="blur"]'),
{
    content: "Check that the Cover snippet has the Blur filter on its background image",
    trigger: "iframe .s_cover span[data-gl-filter='blur']",
    run: () => {}, //it's a check
},
    wTourUtils.changeOption("Parallax", "we-toggler"),
    wTourUtils.changeOption("Parallax", 'we-button[data-select-data-attribute="0"]'),
{
    content: "Check that the data related to the filter have been transferred to the new target",
    trigger: "iframe .s_cover[data-gl-filter='blur']",
    run: () => {}, //it's a check
},
{
    content: "Check that the 'o_modified_image_to_save' class has been transferred to the new target",
    trigger: "iframe .s_cover.o_modified_image_to_save",
    run: () => {}, //it's a check
},
    wTourUtils.changeOption("Parallax", "we-toggler"),
    wTourUtils.changeOption("Parallax", 'we-button[data-select-data-attribute="1"]'),
{
    content: "Check that the 'o_modified_image_to_save' class has been deleted from the old target",
    trigger: "iframe .s_cover:not(.o_modified_image_to_save)",
    run: () => {}, //it's a check
},
{
    content: "Check that the 'o_modified_image_to_save' class has been transferred to the new target",
    trigger: "iframe span.s_parallax_bg.o_modified_image_to_save",
    run: () => {}, //it's a check
},
{
    content: "Check that the data related to the filter have been transferred to the new target",
    trigger: "iframe span.s_parallax_bg[data-gl-filter='blur']",
    run: () => {}, //it's a check
},
]);
});
