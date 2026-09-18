import { stepUtils } from "@web_tour/tour_utils";
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
        trigger:
            ".o_customize_tab [data-container-title='Image'] button[data-action-id='removeMedia']",
        run: "click",
    },
    {
        content: "Check that the snippet editor is not visible",
        trigger: ".o_customize_tab:not(:has([data-container-title='Image']))",
    },
];

registerWebsitePreviewTour(
    "add_and_remove_main_product_image_no_variant",
    {
        url: "/shop?search=Test Remove Image",
    },
    () => [
        ...enterEditModeOfTestProduct(),
        {
            content: "Double click on the product image",
            trigger: ":iframe #o-carousel-product img[alt='Test Remove Image']",
            run: "dblclick",
        },
        {
            content: "Click on the new image",
            trigger:
                ".o_select_media_dialog .o_existing_attachment_cell .o_button_area",
            run: "click",
        },
        {
            content: "Wait for the chosen image to replace the product's",
            trigger:
                ":iframe .o_product_detail_img_wrapper img:not([alt='Test Remove Image'])",
        },
        {
            // the replace re-targets the options a frame later: a Remove found
            // before that belongs to the image the dialog just detached
            content: "Click on Remove in the options of the chosen image",
            trigger:
                ".o_customize_tab [data-container-title='Image']:has(.o-hb-image-size-info:not(:contains(5.9 kB))) button[data-action-id='removeMedia']",
            run: "click",
        },
        {
            content: "Check that the snippet editor is not visible",
            trigger: ".o_customize_tab:not(:has([data-container-title='Image']))",
        },
    ],
);
registerWebsitePreviewTour(
    "remove_main_product_image_with_variant",
    {
        url: "/shop?search=Test Remove Image",
    },
    () => [
        ...enterEditModeOfTestProduct(),
        ...clickOnImgAndWaitForLoad,
        ...clickOnSave(),
        ...clickOnEditAndWaitEditMode(),
        ...clickOnImgAndWaitForLoad,
        ...removeImg,
    ],
);
