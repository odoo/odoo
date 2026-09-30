import {
    addMedia,
    changeOption,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
    changeOptionInPopover,
    clickOnEditAndWaitEditMode,
    assertCssVariable,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "snippet_image_gallery",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_images_wall", name: "Images Wall", groupName: "Images" }),
        ...clickOnSave(),
        {
            content: "Click on an image of the Image Wall",
            trigger: ":iframe .s_image_gallery img",
            run: "click",
        },
        {
            content: "Check that the modal has opened properly",
            trigger: ":iframe .s_gallery_lightbox img",
        },
    ]
);

registerWebsitePreviewTour(
    "snippet_image_gallery_remove",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_image_gallery",
            name: "Image Gallery",
            groupName: "Images",
        }),
        ...clickOnSnippet({
            id: "s_image_gallery",
            name: "Image Gallery",
        }),
        {
            content: "Click on Remove all",
            trigger: "button[data-action-id='removeAllImages']",
            run: "click",
        },
        {
            content: "Click on Add Images",
            trigger: ":iframe span:contains('Add Images')",
            run: "click",
        },
        {
            content: "Click on the first new image",
            trigger: ".o_select_media_dialog .o_button_area[aria-label='s_default_image.jpg']",
            run: "click",
        },
        {
            content: "Click on the second new image",
            trigger: ".o_select_media_dialog .o_button_area[aria-label='s_default_image2.webp']",
            run: "click",
        },
        addMedia(),
        {
            content: "Click on the image of the Image Gallery snippet",
            trigger: ":iframe .s_image_gallery .carousel-item.active  img",
            run: "click",
        },
        {
            content:
                "Check that the Snippet Editor of the clicked image has been loaded with its size",
            trigger:
                ".o-tab-content [data-container-title='Image']:has([title='Size']:text(.+ kB)",
        },
        {
            content: "Click on Remove Block",
            trigger:
                ".o_customize_tab .options-container[data-container-title='Image Gallery'] .oe_snippet_remove",
            run: "click",
        },
        {
            content: "Check that the Image Gallery snippet has been removed",
            trigger: ":iframe #wrap:not(:has(.s_image_gallery))",
        },
    ]
);

registerWebsitePreviewTour(
    "snippet_image_gallery_reorder",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_image_gallery",
            name: "Image Gallery",
            groupName: "Images",
        }),
        {
            content: "Click on the first image of the snippet",
            trigger: ":iframe .s_image_gallery .carousel-item.active img",
            run: "click",
        },
        ...changeOptionInPopover("Image", "Filter", "Blur"),
        {
            content: "Check that the image has the correct filter",
            trigger:
                ".o_customize_tab [data-container-title='Image'] [data-label='Filter'] .o-dropdown:contains('Blur')",
        },
        changeOption("Image", "[data-label='Re-order'] button[data-action-value='next']"),
        {
            content: "Check that the image has been moved",
            trigger: ":iframe .s_image_gallery .carousel-item.active img[data-index='1']",
        },
        {
            content: "Click on the footer to reload the editor panel",
            trigger: ":iframe #footer",
            run: "click",
        },
        {
            content: "Check that the footer options have been loaded",
            trigger: ".o-tab-content [data-container-title='Footer']",
        },
        {
            content: "Click on the moved image",
            trigger: ":iframe .s_image_gallery .carousel-item.active img",
            run: "click",
        },
        {
            content: "Check that the image still has the correct filter",
            trigger:
                ".o_customize_tab [data-container-title='Image'] [data-label='Filter'] .o-dropdown:contains('Blur')",
        },
        {
            content: "Click to access next image",
            trigger: ":iframe .s_image_gallery .carousel-control-next",
            run: "click",
        },
        {
            content: "Check that the option has changed",
            trigger:
                ".o_customize_tab [data-container-title='Image'] [data-label='Filter'] .o-dropdown:contains('None')",
        },
        {
            content: "Click to access previous image",
            trigger: ":iframe .s_image_gallery .carousel-control-prev",
            run: "click",
        },
        {
            content: "Check that the option is restored",
            trigger:
                ".o_customize_tab [data-container-title='Image'] [data-label='Filter'] .o-dropdown:contains('Blur')",
        },
        {
            content: "Change the height of the snippet",
            trigger: `.o_customize_tab [data-container-title="Image Gallery"] [data-label="Height"] input`,
            run: "edit 400",
        },
        changeOption("Image", "[data-label='Re-order'] button[data-action-value='next']"),
        {
            content: "Click on the moved image",
            trigger: ":iframe .s_image_gallery .carousel-item.active img[data-index='2']",
            run: "click",
        },
        assertCssVariable("height", "400px", ":iframe .s_image_gallery"),
    ]
);

registerWebsitePreviewTour(
    "snippet_image_gallery_thumbnail_update",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_image_gallery",
            name: "Image Gallery",
            groupName: "Images",
        }),
        ...clickOnSnippet({
            id: "s_image_gallery",
            name: "Image Gallery",
        }),
        ...changeOptionInPopover("Image Gallery", "Indicators", "Squared Miniatures"),
        changeOption("Image Gallery", "addImage"),
        {
            content: "Click on the default image",
            trigger: ".o_select_media_dialog .o_button_area[aria-label='s_default_image.jpg']",
            run: "click",
        },
        addMedia(),
        {
            content: "Check that the new image has been added",
            trigger: ":iframe .s_image_gallery_indicators_squared:has(img[data-index='3'])",
        },
        {
            content: "Check that the thumbnail of the first image has not been changed",
            trigger:
                ":iframe .s_image_gallery div.carousel-indicators button:first-child[style='background-image: url(/web/image/website.library_image_08)']",
        },
        ...clickOnSave(),
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Check that the thumbnail of the new image is displayed",
            trigger:
                ":iframe .s_image_gallery div.carousel-indicators button:nth-child(4)[style*='s_default_image']",
        },
        {
            content: "Select the first image in the gallery",
            trigger: ":iframe .s_image_gallery .carousel-item:first-child img",
            run: "click",
        },
        {
            content: "Open the replace media dialog",
            trigger: "[data-action-id='replaceMedia']",
            run: "click",
        },
        {
            content: "Pick another image to replace the first one",
            trigger: ".o_select_media_dialog .o_button_area[aria-label='s_default_image_2.jpg']",
            run: "click",
        },
        ...clickOnSave(),
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Check that the first image has been replaced",
            trigger:
                ":iframe .s_image_gallery .carousel-item:first-child img[src*='s_default_image_2']",
        },
        {
            content: "Check that the thumbnail of the first image is updated",
            trigger:
                ":iframe .s_image_gallery div.carousel-indicators button:first-child[style*='s_default_image_2']",
        },
        {
            content: "Select the second image in the gallery",
            trigger: ":iframe .s_image_gallery .carousel-control-next-icon",
            run: "click",
        },
        changeOption("Image", "[data-label='Shape'] .dropdown-toggle"),
        {
            content: "Click on the first image shape",
            trigger: "[data-action-id='setImageShape']",
            run: "click",
        },
        {
            content: "Check that the thumbnail of the second image is an SVG",
            trigger:
                ":iframe .s_image_gallery div.carousel-indicators button:nth-child(2)[style*='data:image/svg+xml']",
        },
    ]
);
