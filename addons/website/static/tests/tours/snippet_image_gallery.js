/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour('snippet_image_gallery', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    ...wTourUtils.dragNDrop({id: 's_images_wall', name: 'Images Wall', groupName: "Images"}),
    ...wTourUtils.clickOnSave(),
    {
        content: 'Click on an image of the Image Wall',
        trigger: ':iframe .s_image_gallery img',
        run: 'click',
    },
    {
        content: 'Check that the modal has opened properly',
        trigger: ':iframe .s_gallery_lightbox img',
    },
]);

wTourUtils.registerWebsitePreviewTour("snippet_image_gallery_remove", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    ...wTourUtils.dragNDrop({
        id: "s_image_gallery",
        name: "Image Gallery",
        groupName: "Images",
}), 
...wTourUtils.clickOnSnippet({
    id: 's_image_gallery',
    name: 'Image Gallery',
}), {
    content: "Click on Remove all",
    trigger: "we-button:has(div:contains('Remove all'))",
    run: "click",
}, {
    content: "Click on Add Images",
    trigger: ":iframe span:contains('Add Images')",
    run: "click",
}, {
    content: "Click on the first new image",
    trigger: ".o_select_media_dialog img[title='s_default_image.jpg']",
    run: "click",
}, {
    content: "Click on the second new image",
    trigger: ".o_select_media_dialog img[title='s_default_image2.jpg']",
    run: "click",
},
    wTourUtils.addMedia(),
   {
    content: "Click on the image of the Image Gallery snippet",
    trigger: ":iframe .s_image_gallery .carousel-item.active  img",
    run: "click",
}, {
    content: "Check that the Snippet Editor of the clicked image has been loaded",
    trigger: "we-customizeblock-options span:contains('Image'):not(:contains('Image Gallery'))",
}, {
    content: "Click on Remove Block",
    trigger: ".o_we_customize_panel we-title:has(span:contains('Image Gallery')) we-button[title='Remove Block']",
    run: "click",
}, {
    content: "Check that the Image Gallery snippet has been removed",
    trigger: ":iframe #wrap:not(:has(.s_image_gallery))",
}]);

wTourUtils.registerWebsitePreviewTour("snippet_image_gallery_reorder", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    ...wTourUtils.dragNDrop({
        id: "s_image_gallery",
        name: "Image Gallery",
        groupName: "Images",
    }),
{
    content: "Click on the first image of the snippet",
    trigger: ":iframe .s_image_gallery .carousel-item.active img",
    run: "click",
},
    wTourUtils.changeOption('ImageToolsAnimate', 'we-select:contains("Filter") we-toggler'),
    wTourUtils.changeOption('ImageToolsAnimate', '[data-gl-filter="blur"]'),
{
    content: "Check that the image has the correct filter",
    trigger: ".snippet-option-ImageToolsAnimate we-select:contains('Filter') we-toggler:contains('Blur')",
}, {
    content: "Click on move to next",
    trigger: ".snippet-option-GalleryElement we-button[data-position='next']",
    run: "click",
}, {
    content: "Check that the image has been moved",
    trigger: ":iframe .s_image_gallery .carousel-item.active img[data-index='1']",
}, {
    content: "Click on the footer to reload the editor panel",
    trigger: ":iframe #footer",
    run: "click",
}, {
    content: "Check that the footer options have been loaded",
    trigger: ".snippet-option-HideFooter we-button:contains('Page Visibility')",
}, {
    content: "Click on the moved image",
    trigger: ":iframe .s_image_gallery .carousel-item.active img[data-index='1'][data-gl-filter='blur']",
    run: "click",
}, {
    content: "Check that the image still has the correct filter",
    trigger: ".snippet-option-ImageToolsAnimate we-select:contains('Filter') we-toggler:contains('Blur')",
}, {
    content: "Click to access next image",
    trigger: ":iframe .s_image_gallery .carousel-control-next",
    run: "click",
}, {
    content: "Check that the option has changed",
    trigger: ".snippet-option-ImageToolsAnimate we-select:contains('Filter') we-toggler:not(:contains('Blur'))",
}, {
    content: "Click to access previous image",
    trigger: ":iframe .s_image_gallery .carousel-control-prev",
    run: "click",
}, {
    content: "Check that the option is restored",
    trigger: ".snippet-option-ImageToolsAnimate we-select:contains('Filter') we-toggler:contains('Blur')",
}]);

wTourUtils.registerWebsitePreviewTour("snippet_image_gallery_thumbnail_update", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    ...wTourUtils.dragNDrop({
        id: "s_image_gallery",
        name: "Image Gallery",
        groupName: "Images",
    }),
    ...wTourUtils.clickOnSnippet({
        id: "s_image_gallery",
        name: "Image Gallery",
    }),
    wTourUtils.changeOption("GalleryImageList", "we-button[data-add-images]"),
{
    content: "Click on the default image",
    trigger: ".o_select_media_dialog img[title='s_default_image.jpg']",
    run: "click",
},
    wTourUtils.addMedia(),
{
    content: "Check that the new image has been added",
    trigger: ":iframe .s_image_gallery:has(img[data-index='3'])",
}, {
    content: "Check that the thumbnail of the first image has not been changed",
    trigger: ":iframe .s_image_gallery ul.carousel-indicators li:first-child[style='background-image: url(/web/image/website.library_image_08)']",
}]);
