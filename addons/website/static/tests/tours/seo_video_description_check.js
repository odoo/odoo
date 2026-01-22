import {
    registerWebsitePreviewTour,
    insertSnippet,
    clickOnSave,
} from "@website/js/tours/tour_utils";


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
            content: "Double Click on the image to open the media dialog",
            trigger: ":iframe .s_text_image img",
            run: "dblclick",
        },
        {
            content: "Go to video tab",
            trigger: ".o_select_media_dialog .nav-link:contains('Video')",
            run: "click",
        },
        {
            content: "Enter a video URL",
            trigger: ".o_select_media_dialog #o_video_text",
            run: `edit https://www.youtube.com/watch?v=Dpq87YCHmJc`,
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
        {
            content: "Check that the video has description as title attribute",
            trigger: ":iframe .s_text_image iframe[title='This is a description of the video']",
        },
    ]
);
