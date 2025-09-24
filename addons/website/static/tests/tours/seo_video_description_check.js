import {
    registerWebsitePreviewTour,
    insertSnippet,
    clickOnSave,
} from "@website/js/tours/tour_utils";

const VIDEO_URL = "https://www.youtube.com/watch?v=Dpq87YCHmJc";

registerWebsitePreviewTour(
    "seo_video_description_check",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_text_image",
            name: "Text - Image",
            groupName: "Content",
        }),
        {
            content: "Click on the image",
            trigger: ":iframe .s_text_image img:not(:visible), :iframe .s_text_image img",
            run: "click",
        },
        {
            content: "Open MediaDialog from an image",
            trigger: ".btn-success[data-action-id='replaceMedia']",
            run: "click",
        },
        {
            content: "Go to video tab",
            trigger: ".o_select_media_dialog .nav-link:contains('Video')",
            run: "click",
        },
        {
            content: "Enter a video URL",
            trigger: ".o_select_media_dialog #o_video_text",
            run: `edit ${VIDEO_URL}`,
        },
        {
            content: "Click on 'add' button",
            trigger: ".modal-footer button:contains('Add')",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Open the site menu",
            trigger: "[data-menu-xmlid='website.menu_site']",
            run: "click",
        },
        {
            content: "Open the optimize SEO dialog",
            trigger: "[data-menu-xmlid='website.menu_optimize_seo']",
            run: "click",
        },
        {
            content: "Check if video description is missing",
            trigger: ".o_seo_images_check input.is-invalid",
        },
        {
            content: "Fill in the video description",
            trigger: ".o_seo_images_check input.is-invalid",
            run: "edit This is a description of the video",
        },
        {
            content: "Check that the warning is gone",
            trigger: ".o_seo_images_check input:not(.is-invalid)",
        },
        {
            content: "Save the SEO configuration",
            trigger: ".oe_seo_configuration .modal-footer .btn-primary",
            run: "click",
        },
    ]
);
