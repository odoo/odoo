import {
    registerWebsitePreviewTour,
    clickOnEditAndWaitEditMode,
    clickOnSave,
    switchToLang,
} from "@website/js/tours/tour_utils";

const openSeoModal = () => [
    {
        content: "click on the site menu",
        trigger: "button[data-menu-xmlid='website.menu_site']",
        run: "click",
    },
    {
        content: "click on the 'Optimize SEO' menu item",
        trigger: "a[data-menu-xmlid='website.menu_optimize_seo']",
        run: "click",
    },
    {
        content: "check if the Optimize SEO modal is successfully triggered",
        trigger: ".oe_seo_configuration",
    },
];

const saveSeoModal = () => [
    {
        content: "Save SEO configuration",
        trigger: ".oe_seo_configuration .modal-footer .btn-primary",
        run: "click",
    },
    {
        content: "Wait for SEO modal to close",
        trigger: "body:not(:has(.modal))",
    },
];

registerWebsitePreviewTour(
    "website.test_website_seo_with_duplicate_images_across_html_fields",
    {},
    () => [
        ...openSeoModal(),
        {
            content: "check that the image from s_banner has been loaded in the modal",
            trigger:
                ".oe_seo_configuration .o_seo_images_check img[src='/web/image/website.s_banner_default_image']",
        },
        {
            content: "Add an alt to one of the images",
            trigger: ".oe_seo_configuration .o_seo_images_check input.form-control.is-invalid",
            run: "edit A very good description",
        },
        ...saveSeoModal(),
        {
            content: "Check that the image's alt was properly edited",
            trigger: ":iframe #wrapwrap #zone_left img[alt='A very good description']",
        },
        ...openSeoModal(),
        {
            content: "Check the modifications are still present in the modal",
            trigger: ".oe_seo_configuration .o_seo_images_check input.form-control.is-valid",
            run() {
                if (this.anchor.value !== "A very good description") {
                    throw new Error("The input should have the image's alt as a value");
                }
            },
        },
    ]
);

registerWebsitePreviewTour(
    "seo_multilang_alt_check",
    // The image and its default language alt text are set up server side.
    {},
    () => [
        ...openSeoModal(),
        {
            content: "The content checks are editable while the translation is up to date",
            trigger: ".o_seo_images_check:not(:has(.o_seo_checks_overlay))",
        },
        {
            content: "Alt text is prefilled from default language",
            trigger: ".o_seo_images_check input.is-valid",
            run() {
                if (this.anchor.value !== "alt text in English") {
                    throw new Error("Alt text should be inherited from the default language");
                }
            },
        },
        {
            content: "Translate alt text to French",
            trigger: ".o_seo_images_check input.is-valid",
            run: "edit alt text in French",
        },
        ...saveSeoModal(),
        {
            content: "Image alt attribute is updated in French",
            trigger: ":iframe .s_text_image img[alt='alt text in French']",
        },
        ...switchToLang("en"),
        {
            content: "Default language alt text is preserved",
            trigger: ":iframe .s_text_image img[alt='alt text in English']",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Select the image",
            trigger: ":iframe .s_text_image img",
            run: "click",
        },
        {
            content: "Describe it again in the default language, which delays its translation",
            trigger: ".hb-row[data-label='Description'] input",
            run: "edit a photograph of the sea && click body",
        },
        ...clickOnSave(),
        ...switchToLang("fr"),
        ...openSeoModal(),
        {
            content: "The content checks are overlaid while the translation is out of date",
            trigger:
                ".o_seo_images_check .o_seo_checks_overlay:contains('Translation may differ from original content')",
        },
        {
            content: "The alt text cannot be edited either",
            trigger: ".o_seo_images_check input:disabled",
        },
        ...saveSeoModal(),
        {
            content: "Saving the dialog left the delayed translation to the user",
            trigger: ":iframe .s_text_image img[alt='alt text in French']",
        },
    ]
);

registerWebsitePreviewTour("seo_video_description_check", {}, () => [
    ...openSeoModal(),
    {
        content: "The video is reported as missing a description",
        trigger: ".o_seo_images_check input.is-invalid",
        run: "edit This is a description of the video",
    },
    {
        content: "The warning is gone",
        trigger: ".o_seo_images_check input.is-valid",
    },
    ...saveSeoModal(),
    {
        content: "The description is applied as the iframe title",
        trigger: ":iframe .media_iframe_video iframe[title='This is a description of the video']",
    },
]);
