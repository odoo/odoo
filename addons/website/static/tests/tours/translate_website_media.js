import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "translate_website_media",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_picture", name: "Title - Image", groupName: "Images" }),
        ...clickOnSave(),
        {
            content: "Change the language to French",
            trigger: ':iframe .js_language_selector .js_change_lang[data-url_code="fr"]',
            run: "click",
        },
        {
            content: "Click edit button",
            trigger: ".o_menu_systray button:contains('Edit').dropdown-toggle",
            run: "click",
        },
        {
            content: "Enable translation",
            trigger: ".o_translate_website_dropdown_item",
            run: "click",
        },
        {
            content: "Close the dialog",
            trigger: ".modal-footer .btn-secondary",
            run: "click",
        },
        // Image translation
        {
            content: "Click on image",
            trigger:
                ":iframe .s_picture img.o_savable_attribute[src='/web/image/website.s_picture_default_image']",
            run: "click",
        },
        {
            content: "Open the media dialog",
            trigger:
                ".options-container [data-action-id='translateMediaSrc'][data-action-param='images']",
            run: "click",
        },
        {
            content: "Select another image",
            trigger: "[aria-label='one_pixel.png']",
            run: "click",
        },
        {
            content: "Check: image has been modified",
            trigger:
                ":iframe .s_picture img.o_savable_attribute:not([src='/web/image/website.s_picture_default_image'])",
        },
        {
            content: "Check: image is marked as translated",
            trigger: ":iframe .s_picture img.o_savable_attribute.o_modified_image_to_save",
        },
        ...clickOnSave(),
        // Translations checks
        {
            content: "Check: image has been replaced",
            trigger:
                ":iframe .s_picture img:not([src='/web/image/website.s_picture_default_image'])",
        },
        {
            content: "open language selector",
            trigger: ":iframe .js_language_selector button:first",
            run: "click",
        },
        {
            content: "return to english version",
            trigger: ':iframe .js_language_selector a[data-url_code="en"]',
            run: "click",
        },
        // Original media checks
        {
            content: "Check: original image is still there",
            trigger: ":iframe .s_picture img[src='/web/image/website.s_picture_default_image']",
        },
    ]
);
