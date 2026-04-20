import {
    registerWebsitePreviewTour,
    insertSnippet,
    clickOnSave,
    switchToLang,
} from "@website/js/tours/tour_utils";
import { stepUtils } from "@web_tour/tour_utils";

const openSeoModal = () => [
    {
        content: "Open site menu",
        trigger: "[data-menu-xmlid='website.menu_site']",
        run: "click",
    },
    {
        content: "Open SEO optimization",
        trigger: "[data-menu-xmlid='website.menu_optimize_seo']",
        run: "click",
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
            content: "Image is missing an alt description",
            trigger: ".o_seo_images_check input.is-invalid",
        },
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
        ...switchToLang("en"),
        {
            content: "Default language alt text is preserved",
            trigger: ":iframe .s_text_image img[alt='alt text in English']",
        },
    ]
);
