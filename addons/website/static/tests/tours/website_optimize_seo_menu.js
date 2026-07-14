import {
    registerWebsitePreviewTour,
    insertSnippet,
    clickOnSave,
    switchToLang,
} from "@website/js/tours/tour_utils";
import { stepUtils } from "@web_tour/tour_utils";

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
    stepUtils.waitIframeIsReady(),
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
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_text_image",
            name: "Text - Image",
            groupName: "Content",
        }),
        ...clickOnSave(),
        ...openSeoModal(),
        {
            content: "Add alt text in default language",
            trigger: ".o_seo_images_check input.is-invalid",
            run: "edit alt text in English",
        },
        {
            content: "Alt warning is resolved",
            trigger: ".o_seo_images_check input:not(.is-invalid)",
        },
        ...saveSeoModal(),
        {
            content: "Image alt attribute is set in default language",
            trigger: ":iframe .s_text_image img[alt='alt text in English']",
        },
        ...switchToLang("fr"),
        {
            content: "The footer still shows its confirmed translation",
            trigger: ":iframe #footer:contains('Liens utiles')",
        },
        ...openSeoModal(),
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
        {
            content: "The delayed footer translation has been confirmed",
            trigger: ":iframe #footer:contains('Handy Links')",
        },
        ...switchToLang("en"),
        {
            content: "Default language alt text is preserved",
            trigger: ":iframe .s_text_image img[alt='alt text in English']",
        },
    ]
);
