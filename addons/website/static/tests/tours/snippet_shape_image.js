import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "snippet_shape_image",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_shape_image", name: "Shape image", groupName: "Content" }),
        {
            content: "Click on the image",
            trigger: ":iframe .s_shape_image img",
            run: "click",
        },
        {
            content: "Click on the remove shape button",
            trigger: "div[data-label='Shape'] i.oi-close",
            run: "click",
        },
        {
            content: "Very if shape is removed",
            trigger: ":iframe .s_shape_image img:not([data-shape])",
        },
    ]
);
