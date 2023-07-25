odoo.define("website.tour.parallax", function (require) {
"use strict";

const tour = require("web_tour.tour");
const wTourUtils = require("website.tour_utils");

const coverSnippet = {id: "s_cover", name: "Cover"};

tour.register("test_parallax", {
    test: true,
    url: "/",
}, [
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.dragNDrop(coverSnippet),
    wTourUtils.clickOnSnippet(coverSnippet),
    wTourUtils.changeOption("BackgroundOptimize", "we-toggler"),
    wTourUtils.changeOption("BackgroundOptimize", 'we-button[data-gl-filter="blur"]'),
{
    content: "Check that the Cover snippet has the Blur filter on its background image",
    trigger: ".s_cover span[data-gl-filter='blur']",
    run: () => {}, //it's a check
},
    wTourUtils.changeOption("Parallax", "we-toggler"),
    wTourUtils.changeOption("Parallax", 'we-button[data-select-data-attribute="0"]'),
{
    content: "Check that the data related to the filter have been transferred to the new target",
    trigger: ".s_cover[data-gl-filter='blur']",
    run: () => {}, //it's a check
},
{
    content: "Check that the 'o_modified_image_to_save' class has been transferred to the new target",
    trigger: ".s_cover.o_modified_image_to_save",
    run: () => {}, //it's a check
},
    wTourUtils.changeOption("Parallax", "we-toggler"),
    wTourUtils.changeOption("Parallax", 'we-button[data-select-data-attribute="1"]'),
{
    content: "Check that the 'o_modified_image_to_save' class has been deleted from the old target",
    trigger: ".s_cover:not(.o_modified_image_to_save)",
    run: () => {}, //it's a check
},
{
    content: "Check that the 'o_modified_image_to_save' class has been transferred to the new target",
    trigger: "span.s_parallax_bg.o_modified_image_to_save",
    run: () => {}, //it's a check
},
{
    content: "Check that the data related to the filter have been transferred to the new target",
    trigger: "span.s_parallax_bg[data-gl-filter='blur']",
    run: () => {}, //it's a check
},
]);
});
