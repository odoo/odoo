import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_image_srcset",
    {
        edition: true,
    },
    () => [
        // Use a snippet whose default image is wide enough for responsive
        // derivatives (see saveModifiedImage: needs width > ~750 / 0.85).
        ...insertSnippet({
            id: "s_contact_info",
            name: "Contact Info",
            groupName: "Contact & Forms",
        }),
        {
            content: "Select image",
            trigger: ":iframe .s_contact_info img",
            run: "click",
        },
        {
            content: "Set low quality",
            trigger:
                ".o_customize_tab div[data-container-title='Image'] div[data-action-id='setImageQuality'] input",
            run: "range 5",
        },
        {
            content: "Wait for image post-process (preview uses a data URL before save)",
            trigger: ":iframe .s_contact_info img[src^='data:image']",
        },
        ...clickOnSave(),
        {
            content: "Wait for the saved page to reload with responsive srcset",
            trigger: ":iframe .s_contact_info img[srcset]",
        },
        {
            content: "Verify responsive candidates persist after save",
            trigger: ":iframe .s_contact_info img[srcset]",
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
