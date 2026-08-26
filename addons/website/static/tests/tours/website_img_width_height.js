import {
    clickOnSave,
    clickOnEditAndWaitEditMode,
    insertSnippet,
    registerWebsitePreviewTour,
    addLanguage,
} from "@website/js/tours/tour_utils";

function changeImage(path, url) {
    return [
        {
            content: "Double click on the image",
            trigger: path,
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
            run: `edit ${url}`,
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

function checkHasCorrectWidthAndHeightAttribute(path) {
    return [
        {
            content: "Check that the image has the width and height attributes",
            trigger: path,
            run: async ({ anchor }) => {
                // wait for the image to load
                if (!anchor.complete) {
                    await new Promise((resolve, reject) => {
                        anchor.onload = resolve;
                        anchor.onerror = reject;
                        if (anchor.complete) {
                            resolve();
                        }
                    });
                }
                const naturalWidth = anchor.naturalWidth;
                const naturalHeight = anchor.naturalHeight;
                if (
                    anchor.getAttribute("width") !== naturalWidth.toString() ||
                    anchor.getAttribute("height") !== naturalHeight.toString()
                ) {
                    throw new Error(
                        `Image should have width "${naturalWidth}" and height "${naturalHeight}", but received "${anchor.getAttribute(
                            "width"
                        )}" "${anchor.getAttribute("height")}"`
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
        ...insertSnippet({
            id: "s_masonry_block_mosaic_template",
            name: "Masonry",
            groupName: "Images",
        }),
        ...changeImage(
            ":iframe .s_masonry_block img:first",
            "/website/static/src/img/snippets_demo/s_accordion_image_default_image.jpg"
        ),
        ...changeImage(
            ":iframe .s_masonry_block img:last",
            "/website/static/src/img/snippets_demo/s_references_2.png"
        ),
        ...clickOnSave(),
        ...checkHasCorrectWidthAndHeightAttribute(":iframe .s_masonry_block img:first"),
        ...checkHasCorrectWidthAndHeightAttribute(":iframe .s_masonry_block img:last"),
        ...clickOnEditAndWaitEditMode(),
        ...addLanguage("Parseltongue", "pa-GB"),
        ...checkHasCorrectWidthAndHeightAttribute(":iframe .s_masonry_block img:first"),
        ...checkHasCorrectWidthAndHeightAttribute(":iframe .s_masonry_block img:last"),
        {
            content: "Open the Edit dropdown",
            trigger:
                "body:has(:iframe body[is-ready=true]) .o_menu_systray button:contains('Edit').dropdown-toggle",
            run: "click",
        },
        {
            content: "Enter translate mode",
            trigger: ".o_translate_website_dropdown_item",
            run: "click",
        },
        {
            content: "Close the translation dialog",
            trigger: ".modal-footer .btn-secondary",
            run: "click",
        },
        {
            content: "Check that we are in translate mode",
            trigger: ":iframe .s_masonry_block img.o_savable_attribute",
        },
        ...changeImage(
            ":iframe .s_masonry_block img:first",
            "/website/static/src/img/snippets_demo/s_references_3.png"
        ),
        ...clickOnSave(),
        {
            content:
                "Check that the image has no width or height attributes because it is a translated media",
            trigger: ":iframe html[lang*='pa-GB'] .s_masonry_block img:first",
            run: async ({ anchor }) => {
                if (anchor.getAttribute("width") || anchor.getAttribute("height")) {
                    throw new Error(
                        `Image should have no width or height attributes, but received width="${anchor.getAttribute(
                            "width"
                        )}" and height="${anchor.getAttribute("height")}"`
                    );
                }
            },
        },
        ...checkHasCorrectWidthAndHeightAttribute(":iframe .s_masonry_block img:last"),
    ]
);
