import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_image_srcset",
    {
        undeterministicTour_doNotCopy: true, // Remove this key to make the tour failed. ( It removes delay between steps )
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_picture",
            name: "Title - Image",
            groupName: "Images",
        }),
        {
            content: "Select image",
            trigger: ":iframe .s_picture img",
            run: "click",
        },
        {
            content: "Set low quality",
            trigger:
                ".o_customize_tab div[data-container-title='Image'] div[data-action-id='setImageQuality'] input",
            run: "range 5",
        },
        {
            content: "Wait for image update: NOT original image",
            trigger: ':iframe .s_picture img:not([src$="s_picture_default_image"])',
        },
        ...clickOnSave(),
        {
            content: "Wait for the saved page to reload with the modified image",
            trigger: ':iframe .s_picture img:not([src$="s_picture_default_image"])',
        },
        {
            content: "Verify responsive candidates persist after save",
            trigger: ':iframe .s_picture img:not([src$="s_picture_default_image"])',
            run() {
                const img = this.anchor;
                if (!img?.srcset) {
                    throw new Error("Modified image should have a srcset");
                }
                const candidates = img.srcset
                    .split(",")
                    .map((entry) => entry.trim())
                    .filter(Boolean);
                if (candidates.length < 2) {
                    throw new Error("Expected multiple srcset candidates, got: " + img.srcset);
                }
            },
        },
    ]
);
