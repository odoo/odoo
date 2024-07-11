/** @odoo-module */

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour('website_image_quality', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    {
        content: "Select image",
        trigger: 'iframe .s_text_image img',
    },
    {
        content: "Set low quality",
        trigger: 'we-customizeblock-options:has(we-title:contains("Image")) we-range[data-set-quality] input',
        run: 'range 5',
    },
    {
        content: "Wait for image update: NOT original image",
        trigger: 'iframe .s_text_image img:not([src$="s_text_image_default_image"])',
        run: () => {}, // It is a check.
    },
    {
        content: "Check image size",
        // Reached size cannot be hardcoded because it changes with
        // different versions of Chrome.
        trigger: 'we-customizeblock-options:has(we-title:contains("Image")) .o_we_image_weight:contains(" kb"):not(:contains("41.5 kb"))',
        run() {
            // Make sure the reached size is smaller than the original one.
            if (parseFloat(this.$anchor[0].innerText) >= 47.5) {
                console.error("Image size should be smaller than original");
            }
        },
    },
    {
        content: "Set high quality",
        trigger: 'we-customizeblock-options:has(we-title:contains("Image")) we-range[data-set-quality] input',
        run: 'range 99',
    },
    {
        content: "Wait for image update: back to original image",
        trigger: 'iframe .s_text_image img[src$="0sOnkdNPFFV0lRVRLK+B7PJ5F4If2IY8ngQsDP//Z"]',
        run: () => {}, // It is a check.
    },
    {
        content: "Check image size",
        trigger: 'we-customizeblock-options:has(we-title:contains("Image")) .o_we_image_weight:contains("41.5 kb")',
        run: () => {}, // It is a check.
    },
]);
