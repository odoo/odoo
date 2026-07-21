import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "cta_mockups_shape_color_option",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_cta_mockups",
            groupName: "Content",
        }),
        {
            content: "Click on the laptop shape",
            trigger: ":iframe .s_cta_mockups img[data-shape$='macbook_front']",
            run: "click",
        },
        {
            content: "Check that the image shape color option appears in the sidebar",
            trigger: "#oe_snippets .o_we_image_shape .o_we_color_preview",
        },
    ]
);
