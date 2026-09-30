import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const clickOnImgAndWaitForLoad = [
    {
        content: "Click on the product image",
        trigger: ":iframe #o-carousel-product img[alt='Test Remove Image']",
        run: "click",
    },
    {
        content: "Check that the snippet editor of the clicked image has been loaded",
        trigger: ".o_customize_tab [data-container-title='Image']",
    },
];
const enterEditModeOfTestProduct = () => [
    {
        content: "Click on the product anchor",
        trigger: ":iframe a:contains('Test Remove Image')",
        run: "click",
    },
    {
        content: "Check that the product page is loaded",
        trigger: ":iframe .o_wsale_product_page",
    },
    ...clickOnEditAndWaitEditMode(),
];

registerWebsitePreviewTour("website_sale.add_and_remove_main_product_image_no_variant", {}, () => [
    ...enterEditModeOfTestProduct(),
    {
        content: "Double click on the product image",
        trigger: ":iframe #o-carousel-product img[alt='Test Remove Image']",
        run: "dblclick",
    },
    {
        content: "Click on the new image",
        trigger: ".o_select_media_dialog .o_existing_attachment_cell .o_button_area",
        run: "click",
    },
    {
        content: "Check that the snippet editor of the clicked image has been loaded",
        trigger: ".o_customize_tab [data-container-title='Image']",
    },
    {
        content: "Ensure the new image is really loaded in DOM before click on remove",
        trigger: `:iframe .o_product_detail_img_wrapper img:not([alt='Test Remove Image'])`,
    },
    // Double check not placeholder image is loaded with :not(:contains(3.7 kB)
    {
        content: "Click on Remove",
        trigger:
            ".o_customize_tab [data-container-title='Image']:has(.o-hb-image-size-info:not(:contains(3.7 kB))) button[data-action-id='removeMedia']",
        run: "click",
    },
    // If the snippet editor is not visible, the remove process is considered as finished.
    {
        content: "Check that the snippet editor is not visible",
        trigger: ".o_customize_tab:not(:has([data-container-title='Image']))",
    },
]);
registerWebsitePreviewTour("website_sale.remove_main_product_image_with_variant", {}, () => [
    ...enterEditModeOfTestProduct(),
    ...clickOnImgAndWaitForLoad,
    ...clickOnSave(),
    ...clickOnEditAndWaitEditMode(),
    ...clickOnImgAndWaitForLoad,
    {
        content: "Ensure the image is really loaded in DOM before click on remove",
        trigger: `:iframe .o_product_detail_img_wrapper img`,
    },
    {
        content: "Click on Remove",
        trigger:
            ".o_customize_tab [data-container-title='Image']:has(.o-hb-image-size-info) button[data-action-id='removeMedia']",
        run: "click",
    },
    // If the snippet editor is not visible, the remove process is considered as finished.
    {
        content: "Check that the snippet editor is not visible",
        trigger: ".o_customize_tab:not(:has([data-container-title='Image']))",
    },
]);
registerWebsitePreviewTour("website_sale.reorder_and_remove_product_video", {}, () => [
    ...enterEditModeOfTestProduct(),
    {
        content: "Show the slide of the product video",
        trigger: ":iframe .carousel-indicators li[data-bs-slide-to='1']",
        run: "click",
    },
    {
        content: "Click on the product video",
        trigger: ":iframe #o-carousel-product .carousel-item.active [data-embedded='video']",
        run: "click",
    },
    {
        content: "Move the video to the last position",
        trigger: ".o_customize_tab [data-action-id='setPosition'][data-action-value='last']",
        run: "click",
    },
    {
        content: "Check that the video is the last media",
        trigger: ":iframe .carousel-indicators li:last-child .o_product_video_thumb",
    },
    {
        content: "Check that the video slide is shown",
        trigger: ":iframe .carousel-item.active:last-child [data-embedded='video']",
    },
    {
        content: "Remove the video",
        trigger: ".o_customize_tab [data-action-id='removeMedia']",
        run: "click",
    },
    {
        content: "Check that the video is removed",
        trigger: ":iframe .carousel-indicators:not(:has(.o_product_video_thumb))",
    },
]);
