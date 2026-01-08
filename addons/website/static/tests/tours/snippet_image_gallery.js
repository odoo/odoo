/** @odoo-module */

import {
    addMedia,
    changeOption,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
    assertCssVariable,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('snippet_image_gallery', {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({id: 's_images_wall', name: 'Images Wall', groupName: "Images"}),
    ...clickOnSave(),
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

registerWebsitePreviewTour("snippet_image_gallery_remove", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({
        id: "s_image_gallery",
        name: "Image Gallery",
        groupName: "Images",
}),
...clickOnSnippet({
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
    addMedia(),
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

registerWebsitePreviewTour("snippet_image_gallery_reorder", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({
        id: "s_image_gallery",
        name: "Image Gallery",
        groupName: "Images",
    }),
{
    content: "Click on the first image of the snippet",
    trigger: ":iframe .s_image_gallery .carousel-item.active img",
    run: "click",
},
    changeOption('ImageTools', 'we-select:contains("Filter") we-toggler'),
    changeOption('ImageTools', '[data-gl-filter="blur"]'),
{
    content: "Check that the image has the correct filter",
    trigger: ".snippet-option-ImageTools we-select:contains('Filter') we-toggler:contains('Blur')",
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
    trigger: ".snippet-option-ImageTools we-select:contains('Filter') we-toggler:contains('Blur')",
}, {
    content: "Click to access next image",
    trigger: ":iframe .s_image_gallery .carousel-control-next",
    run: "click",
}, {
    content: "Check that the option has changed",
    trigger: ".snippet-option-ImageTools we-select:contains('Filter') we-toggler:not(:contains('Blur'))",
}, {
    content: "Click to access previous image",
    trigger: ":iframe .s_image_gallery .carousel-control-prev",
    run: "click",
}, {
    content: "Check that the option is restored",
    trigger: ".snippet-option-ImageTools we-select:contains('Filter') we-toggler:contains('Blur')",
}, {
    content: "Change the height of the snippet",
    trigger: `.snippet-option-ScrollButton [data-name="fixed_height_opt"] input`,
    run: "edit 400",
}, {
    content: "Click on move to next",
    trigger: ".snippet-option-GalleryElement we-button[data-position='next']",
    run: "click",
}, {
    content: "Check that the image has been moved",
    trigger: ":iframe .s_image_gallery .carousel-item.active img[data-index='2']",
}, {
    content: "Click on the moved image",
    trigger: ":iframe .s_image_gallery .carousel-item.active img[data-index='2']",
},
    assertCssVariable("height", "400px", ":iframe .s_image_gallery"),
]);

registerWebsitePreviewTour("snippet_image_gallery_thumbnail_update", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({
        id: "s_image_gallery",
        name: "Image Gallery",
        groupName: "Images",
    }),
    ...clickOnSnippet({
        id: "s_image_gallery",
        name: "Image Gallery",
    }),
    changeOption("GalleryImageList", "we-button[data-add-images]"),
{
    content: "Click on the default image",
    trigger: ".o_select_media_dialog img[title='s_default_image.jpg']",
    run: "click",
},
    addMedia(),
{
    content: "Check that the new image has been added",
    trigger: ":iframe .s_image_gallery:has(img[data-index='3'])",
}, {
    content: "Check that the thumbnail of the first image has not been changed",
    trigger: ":iframe .s_image_gallery div.carousel-indicators button:first-child[style='background-image: url(/web/image/website.library_image_08)']",
}]);
