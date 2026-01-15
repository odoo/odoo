import { clickOnSave, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

// As admin, add a YouTube video iframe in a `sanitize_overridable` HTML field.
registerWebsitePreviewTour("website_designer_iframe_video",
    {
        url: "/test_website/model_item/1",
        edition: true,
    },
    () => [
        {
            content: "As administrator, add a video block to the description field",
            trigger: `.o_block_tab:not(.o_we_ongoing_insertion) #snippet_content .o_snippet[name="Video"].o_draggable .o_snippet_thumbnail`,
            run: "drag_and_drop :iframe .o_test_website_description",
        },
        {
            content: "Add a video URL",
            trigger: ".o_select_media_dialog #o_video_text",
            run: `edit https://www.youtube.com/watch?v=G8b4UZIcTfg`,
        },
        {
            content: "Add the video",
            trigger: ".o_select_media_dialog .modal-footer .btn-primary",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Check that the video was correctly saved",
            trigger: ":iframe .media_iframe_video[data-oe-expression*='G8b4UZIcTfg']",
            run: () => {},
        },
    ]
);

// Check that a restricted editor can edit the field content (even with
// a video iframe).
registerWebsitePreviewTour("website_restricted_editor_iframe_video", {
        url: "/test_website/model_item/1",
        edition: true,
    },
    () => [
        {
            content: "Check that the video iframe was correctly restored after saving the changes",
            trigger:
                ":iframe [data-oe-field]:not([data-oe-sanitize-prevent-edition]) .media_iframe_video[data-oe-expression*='G8b4UZIcTfg']",
            run: () => {},
        },
        {
            content: "As a restricted editor, edit the HTML field content",
            trigger: ":iframe .o_test_website_description",
            run: "editor I can still edit the HTML field",
        },
        ...clickOnSave(),
        {
            content: "Check that the HTML content (with a video iframe) was correctly updated",
            trigger:
                ":iframe .o_test_website_description:contains('I can still edit the HTML field')",
            run: () => {},
        },
    ]
);
