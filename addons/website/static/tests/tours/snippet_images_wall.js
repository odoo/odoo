/** @odoo-module **/

import wTourUtils from "website.tour_utils";

const selectSignImageStep = {
    content: "Click on sign image",
    extra_trigger: ".o_we_customize_panel:not(:has(.snippet-option-gallery_img))",
    trigger: "iframe .s_image_gallery img[data-original-src*='sign']",
};
// Without reselecting the image, the tour manages to click on the
// move button before the active image is updated.
const reselectSignImageSteps = [{
    content: "Select footer",
    trigger: "iframe footer",
}, selectSignImageStep];

wTourUtils.registerWebsitePreviewTour("snippet_images_wall", {
    test: true,
    url: "/",
    edition: true,
}, [
    wTourUtils.dragNDrop({
        id: "s_images_wall",
        name: "Images Wall",
}), wTourUtils.clickOnSnippet({
    id: "s_image_gallery",
    name: "Images Wall",
}),
selectSignImageStep,
{
    content: "Click on move to previous",
    trigger: ".snippet-option-gallery_img we-button[data-position='prev']",
}, {
    content: "Check if sign is in second column",
    trigger: "iframe .s_image_gallery .o_masonry_col:nth-child(2):has(img[data-index='1'][data-original-src*='sign'])",
    run: () => {}, // This is a check.
},
...reselectSignImageSteps,
{
    content: "Click on move to first",
    trigger: ".snippet-option-gallery_img we-button[data-position='first']",
}, {
    content: "Check if sign is in first column",
    trigger: "iframe .s_image_gallery .o_masonry_col:nth-child(1):has(img[data-index='0'][data-original-src*='sign'])",
    run: () => {}, // This is a check.
},
...reselectSignImageSteps,
{
    content: "Click on move to previous",
    trigger: ".snippet-option-gallery_img we-button[data-position='prev']",
}, {
    content: "Check if sign is in third column",
    trigger: "iframe .s_image_gallery .o_masonry_col:nth-child(3):has(img[data-index='5'][data-original-src*='sign'])",
    run: () => {}, // This is a check.
},
...reselectSignImageSteps,
{
    content: "Click on move to next",
    trigger: ".snippet-option-gallery_img we-button[data-position='next']",
}, {
    content: "Check if sign is in first column",
    trigger: "iframe .s_image_gallery .o_masonry_col:nth-child(1):has(img[data-index='0'][data-original-src*='sign'])",
    run: () => {}, // This is a check.
},
...reselectSignImageSteps,
{
    content: "Click on move to last",
    trigger: ".snippet-option-gallery_img we-button[data-position='last']",
}, {
    content: "Check layout",
    trigger: "iframe .s_image_gallery .o_masonry_col:nth-child(3):has(img[data-index='5'][data-original-src*='sign'])",
    run: () => {}, // This is a check.
}]);
