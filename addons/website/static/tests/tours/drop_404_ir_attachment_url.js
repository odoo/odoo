import {
    insertSnippet,
    registerWebsitePreviewTour,
    changeImageShape,
} from "@website/js/tours/tour_utils";
import { onceAllImagesLoaded } from "@website/utils/images";

registerWebsitePreviewTour(
    "drop_404_ir_attachment_url",
    {
        // Remove this key to get warning should not have any "characterData", "remove"
        // or "add" mutations in current step when you update the selection
        undeterministicTour_doNotCopy: true,
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_404_snippet",
            name: "404 Snippet",
            groupName: "Images",
        }),
        {
            content: "Click on the snippet image",
            trigger: ":iframe .s_404_snippet img",
            run: "click",
        },
        {
            trigger: "[data-action-id='replaceMedia']",
        },
        {
            content: "Once the image UI appears, check the image has no size (404)",
            trigger: ":iframe .s_404_snippet img",
            async run() {
                const imgEl = this.anchor;
                await onceAllImagesLoaded(imgEl);
                if (imgEl.naturalWidth !== 0 || imgEl.naturalHeight !== 0) {
                    throw new Error("This is supposed to be a 404 image");
                }
            },
        },
        ...changeImageShape(),
        {
            content:
                "Once the shape is applied, check the image has now a size (placeholder image)",
            trigger: ':iframe .s_404_snippet img[src^="data:"]',
            async run() {
                const imgEl = this.anchor;
                await onceAllImagesLoaded(imgEl);
                if (imgEl.naturalWidth === 0 || imgEl.naturalHeight === 0) {
                    throw new Error(
                        "Even though the original image was a 404, the option should have been applied on the placeholder image"
                    );
                }
            },
        },
    ]
);
