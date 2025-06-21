/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

const clickOnImgAndWaitForLoad = [
    {
        content: "Click on the product image",
        trigger: "iframe #o-carousel-product img[alt='Test Remove Image']",
    },
    {
        content: "Check that the snippet editor of the clicked image has been loaded",
        trigger: "we-customizeblock-options:has(we-title:contains('Re-order'))",
        run: () => null,
    },
];
const enterEditModeOfTestProduct = () => [
    {
        content: "Click on the product anchor",
        trigger: "iframe a:contains('Test Remove Image')",
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
];

const removeImg = [
    {
        content: "Click on Remove",
        trigger: "we-customizeblock-options:has(we-title:contains('Image')) we-button[data-name='media_wsale_remove']",
    },
    // If the snippet editor is not visible, the remove process is considered as
    // finished.
    {
        content: "Check that the snippet editor is not visible",
        trigger: ".o_we_customize_panel:not(:has(we-customizeblock-options:has(we-title:contains('Re-order'))))",
        run: () => null,
    },
];

wTourUtils.registerWebsitePreviewTour("add_and_remove_main_product_image_no_variant", {
    url: "/shop?search=Test Remove Image",
    test: true,
}, () => [
    ...enterEditModeOfTestProduct(),
    {
        content: "Double click on the product image",
        trigger: "iframe #o-carousel-product img[alt='Test Remove Image']",
        run: "dblclick",
    },
    {
        content: "Click on the new image",
        trigger: ".o_select_media_dialog img[title='s_default_image.jpg']",
    },
    {
        content: "Check that the snippet editor of the clicked image has been loaded",
        trigger: "we-customizeblock-options:has(we-title:contains('Re-order'))",
        run: () => null,
    },
    ...removeImg,
]);
wTourUtils.registerWebsitePreviewTour("remove_main_product_image_with_variant", {
    url: "/shop?search=Test Remove Image",
    test: true,
}, () => [
    ...enterEditModeOfTestProduct(),
    ...clickOnImgAndWaitForLoad,
    ...wTourUtils.clickOnSave(),
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    ...clickOnImgAndWaitForLoad,
    ...removeImg,
]);
