import {
    clickOnSave,
    clickOnEditAndWaitEditMode,
    clickOnEditAndWaitEditModeInTranslatedPage,
    insertSnippet,
    registerWebsitePreviewTour,
    addLanguage,
} from "@website/js/tours/tour_utils";

const imageUrls = {
    "600x400": "/website/static/src/img/snippets_demo/s_accordion_image_default_image.jpg",
    "385x200": "/website/static/src/img/snippets_demo/s_references_2.png",
};

function changeImage(width, height) {
    return [
        {
            content: "Double click on the image",
            trigger: ":iframe .s_picture img",
            run: "dblclick",
        },
        {
            content: 'Click "Add URL"',
            trigger: ".o_upload_media_url_button",
            run: "click",
        },
        {
            content: "Add an image URL",
            trigger: "input.o_we_url_input",
            run: `edit ${imageUrls[`${width}x${height}`]}`,
        },
        {
            trigger: ".o_we_url_success",
        },
        {
            content: 'Click "Add URL" really adding image',
            trigger: ".o_upload_media_url_button",
            run: "click",
        },
    ];
}

function checkWidthAndHeight(width, height) {
    return [
        {
            content: "Check that the image has the width and height attributes",
            trigger: ":iframe .s_picture img",
            run: async ({ anchor }) => {
                if (anchor.width !== width || anchor.height !== height) {
                    throw new Error(
                        `Image should have width "${width}" and height "${height}", but received "${anchor.width} / ${anchor.height}"`
                    );
                }
            },
        },
    ];
}

registerWebsitePreviewTour(
    "website_img_width_height",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_picture", name: "Title - Image", groupName: "Images" }),
        ...changeImage(600, 400),
        ...clickOnSave(),
        ...checkWidthAndHeight(600, 400),
        ...clickOnEditAndWaitEditMode(),
        ...changeImage(385, 200),
        ...clickOnSave(),
        ...checkWidthAndHeight(385, 200),
        ...clickOnEditAndWaitEditMode(),
        ...addLanguage("French / Français", "fr-FR"),
        ...checkWidthAndHeight(385, 200),
        ...clickOnEditAndWaitEditModeInTranslatedPage(),
        ...changeImage(600, 400),
        {
            content:
                "Check that the image has no width or height attributes because it is a translated media",
            trigger: ":iframe .s_picture img",
            run: async ({ anchor }) => {
                if (anchor.getAttribute("width") || anchor.getAttribute("height")) {
                    throw new Error(
                        `Image should have no width or height attributes, but received width="${anchor.width}" and height="${anchor.height}"`
                    );
                }
            },
        },
    ]
);
