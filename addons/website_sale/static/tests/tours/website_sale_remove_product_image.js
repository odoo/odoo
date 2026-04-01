import { stepUtils } from "@web_tour/tour_utils";
import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

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
    stepUtils.waitIframeIsReady(),
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

const removeImg = [
    {
        content: "Click on Remove",
        trigger: ".o_customize_tab [data-container-title='Image'] button[data-action-id='removeMedia']",
        run: "click",
    },
    // If the snippet editor is not visible, the remove process is considered as
    // finished.
    {
        content: "Check that the snippet editor is not visible",
        trigger: ".o_customize_tab:not(:has([data-container-title='Image']))",
    },
];

registerWebsitePreviewTour("add_and_remove_main_product_image_no_variant", {
    url: "/shop?search=Test Remove Image",
}, () => [
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
    ...removeImg,
]);
registerWebsitePreviewTour("remove_main_product_image_with_variant", {
    url: "/shop?search=Test Remove Image",
}, () => [
    ...enterEditModeOfTestProduct(),
    ...clickOnImgAndWaitForLoad,
    ...clickOnSave(),
    ...clickOnEditAndWaitEditMode(),
    ...clickOnImgAndWaitForLoad,
    ...removeImg,
]);
