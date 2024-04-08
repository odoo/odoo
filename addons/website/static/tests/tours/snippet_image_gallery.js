odoo.define("website.tour.snippet_image_gallery", function (require) {
"use strict";

const tour = require("web_tour.tour");
const wTourUtils = require("website.tour_utils");

tour.register("snippet_image_gallery", {
    test: true,
    url: "/",
}, [
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.dragNDrop({
        id: "s_image_gallery",
        name: "Image Gallery",
}), wTourUtils.clickOnSnippet({
    id: 's_image_gallery',
    name: 'Image Gallery',
}), {
    content: "Click on Remove all",
    trigger: "we-button:has(div:contains('Remove all'))",
}, {
    content: "Click on Add Images",
    trigger: "span:contains('Add Images')",
}, {
    content: "Click on the first new image",
    trigger: ".o_select_media_dialog img[title='s_default_image.jpg']",
}, {
    content: "Click on the second new image",
    trigger: ".o_select_media_dialog img[title='s_default_image2.jpg']",
},
    wTourUtils.addMedia(),
   {
    content: "Click on the image of the Image Gallery snippet",
    trigger: ".s_image_gallery .carousel-item.active  img",
}, {
    content: "Check that the Snippet Editor of the clicked image has been loaded",
    trigger: "we-customizeblock-options span:contains('Image'):not(:contains('Image Gallery'))",
    run: () => null,
},
    wTourUtils.changeOption('ImageOptimize', 'we-select:contains("Filter") we-toggler'),
    wTourUtils.changeOption('ImageOptimize', '[data-gl-filter="blur"]'),
{
    content: "Check that the image has the correct filter",
    trigger: ".snippet-option-ImageOptimize we-select:contains('Filter') we-toggler:contains('Blur')",
    run: () => null, // This is a check.
}, {
    content: "Click on move to next",
    trigger: ".snippet-option-gallery_img we-button[data-position='next']",
}, {
    content: "Check that the image has been moved",
    trigger: ".s_image_gallery .carousel-item.active img[data-index='1']",
    run: () => null, // This is a check.
}, {
    content: "Click on the footer to reload the editor panel",
    trigger: "#footer",
}, {
    content: "Check that the footer options have been loaded",
    trigger: ".snippet-option-HideFooter we-button:contains('Page Visibility')",
    run: () => null, // This is a check.
}, {
    content: "Click on the moved image",
    trigger: "#wrap .s_image_gallery .carousel-item.active img[data-index='1'][data-gl-filter='blur']",
}, {
    content: "Check that the image still has the correct filter",
    trigger: ".snippet-option-ImageOptimize we-select:contains('Filter') we-toggler:contains('Blur')",
    run: () => null, // This is a check.
}, {
    content: "Click to access next image",
    trigger: ".s_image_gallery .carousel-control-next",
}, {
    content: "Check that the option has changed",
    trigger: ".snippet-option-ImageOptimize we-select:contains('Filter') we-toggler:not(:contains('Blur'))",
    run: () => null, // This is a check.
}, {
    content: "Click to access previous image",
    trigger: ".s_image_gallery .carousel-control-prev",
}, {
    content: "Check that the option is restored",
    trigger: ".snippet-option-ImageOptimize we-select:contains('Filter') we-toggler:contains('Blur')",
    run: () => null, // This is a check.
}, {
    content: "Click on Remove Block",
    trigger: ".o_we_customize_panel we-title:has(span:contains('Image Gallery')) we-button[title='Remove Block']",
}, {
    content: "Check that the Image Gallery snippet has been removed",
    trigger: "#wrap:not(:has(.s_image_gallery))",
    run: () => null,
}]);
});
