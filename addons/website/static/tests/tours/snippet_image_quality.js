import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour('website_image_quality', {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    }),
    {
        content: "Select image",
        trigger: ':iframe .s_text_image img',
        run: "click",
    },
    {
        content: "Set low quality",
        trigger: ".o_customize_tab div[data-container-title='Image'] div[data-action-id='setImageQuality'] input",
        run: 'range 5',
    },
    {
        content: "Wait for image update: NOT original image",
        trigger: ':iframe .s_text_image img:not([src$="s_text_image_default_image"])',
    },
    {
        content: "Check image size",
        // Reached size cannot be hardcoded because it changes with
        // different versions of Chrome.
        trigger: ".o_customize_tab [data-container-title='Image'] span[title='Size']:contains(' kb'):not(:contains('42.9 kb'))",
        run() {
            // Make sure the reached size is smaller than the original one.
            if (parseFloat(this.anchor.innerText) >= 42.9) {
                throw new Error("Image size should be smaller than original");
            }
        },
    },
    {
        content: "Set high quality",
        trigger: ".o_customize_tab div[data-container-title='Image'] div[data-action-id='setImageQuality'] input",
        run: 'range 99',
    },
    {
        content: "Wait for image update: back to original image",
        trigger: ':iframe .s_text_image img[src$="S55YBaZ4YLuRoopv55ZIqZKBC8uATEEUgAAA="]',
    },
    {
        content: "Check image size",
        trigger: ".o_customize_tab [data-container-title='Image'] span[title='Size']:contains('22.8')",
    },
]);
