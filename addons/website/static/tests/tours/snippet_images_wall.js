/** @odoo-module **/

import tour from "web_tour.tour";
import wTourUtils from "website.tour_utils";

tour.register("snippet_images_wall", {
    test: true,
    url: "/",
}, [
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.dragNDrop({
        id: "s_images_wall",
        name: "Images Wall",
}), wTourUtils.clickOnSnippet({
    id: "s_image_gallery",
    name: "Images Wall",
}), {
    // Prefixing selectors with #wrap to avoid matching droppable block.
    content: "Click on third image",
    trigger: "#wrap .s_image_gallery img[data-index='2']",
}, {
    content: "Click on move to previous",
    trigger: ".snippet-option-gallery_img we-button[data-position='prev']",
}, {
    content: "Click on move to first",
    extra_trigger: "#wrap .s_image_gallery .o_masonry_col:nth-child(2):has(img[data-index='1'][data-original-src*='sign'])",
    trigger: ".snippet-option-gallery_img we-button[data-position='first']",
}, {
    content: "Click on move to previous",
    extra_trigger: "#wrap .s_image_gallery .o_masonry_col:nth-child(1):has(img[data-index='0'][data-original-src*='sign'])",
    trigger: ".snippet-option-gallery_img we-button[data-position='prev']",
}, {
    content: "Click on move to next",
    extra_trigger: "#wrap .s_image_gallery .o_masonry_col:nth-child(3):has(img[data-index='5'][data-original-src*='sign'])",
    trigger: ".snippet-option-gallery_img we-button[data-position='next']",
}, {
    content: "Click on move to last",
    extra_trigger: "#wrap .s_image_gallery .o_masonry_col:nth-child(1):has(img[data-index='0'][data-original-src*='sign'])",
    trigger: ".snippet-option-gallery_img we-button[data-position='last']",
}, {
    content: "Check layout",
    trigger: "#wrap .s_image_gallery .o_masonry_col:nth-child(3):has(img[data-index='5'][data-original-src*='sign'])",
    run: () => {}, // This is a check.
}]);
