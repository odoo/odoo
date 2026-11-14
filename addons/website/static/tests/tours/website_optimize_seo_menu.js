import { rpc } from "@web/core/network/rpc";
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
            trigger: ".o_hb_row[data-label='Description'] input",
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

const brokenLinkRow = (label) =>
    `.oe_seo_configuration .row.align-items-center:has(label[title='${label}'])`;

const mockLinkChecks = () => [
    {
        content: "Mock the link checks, the test server refuses requests without session",
        trigger: "body",
        run() {
            const fetch = window.fetch;
            window.fetch = (url, options) => {
                if (options?.credentials !== "omit") {
                    return fetch(url, options);
                }
                const { pathname } = new URL(url, window.location.origin);
                const status = pathname.startsWith("/broken") ? 404 : 200;
                return Promise.resolve(new Response("", { status }));
            };
        },
    },
];

registerWebsitePreviewTour(
    "seo_broken_links_multilang",
    // The broken links and their French translation are set up server side.
    {},
    () => [
        ...mockLinkChecks(),
        ...openSeoModal(),
        {
            content: "The broken links are checked on the French page too",
            trigger: `${brokenLinkRow("lien texte")} input.is-invalid`,
        },
        {
            content: "Only the broken links are listed: the text link and the image link",
            trigger: ".oe_seo_configuration",
            run() {
                const rows = this.anchor.querySelectorAll(".row.align-items-center:has(.btn-danger)");
                if (rows.length !== 2) {
                    throw new Error(`Expected 2 broken links, found ${rows.length}`);
                }
            },
        },
        {
            content: "The stored href is proposed, not the one of the French URL",
            trigger: `${brokenLinkRow("lien texte")} input`,
            run() {
                if (this.anchor.value !== "/broken-text") {
                    throw new Error(`Expected '/broken-text', got '${this.anchor.value}'`);
                }
            },
        },
        {
            content: "Replace the text link",
            trigger: `${brokenLinkRow("lien texte")} input`,
            run: "edit /contactus",
        },
        {
            content: "Check the new link",
            trigger: `${brokenLinkRow("lien texte")} button.btn-primary:enabled`,
            run: "click",
        },
        {
            content: "The new link is valid",
            trigger: `${brokenLinkRow("lien texte")} input.is-valid`,
        },
        {
            content: "Remove the image link",
            trigger:
                ".oe_seo_configuration .row.align-items-center:has(label .oi[data-icon='image']) .btn-danger",
            run: "click",
        },
        {
            content: "The image link is not listed anymore",
            trigger: ".oe_seo_configuration:not(:has(label .oi[data-icon='image']))",
        },
        ...saveSeoModal(),
        {
            content: "The text link is fixed on the French page",
            trigger: ":iframe #wrap a[href='/contactus']:contains('lien texte')",
        },
        {
            content: "The image link is removed but the image is kept",
            trigger: ":iframe #wrap:not(:has(a[href='/broken-image'])) img[alt='alt image']",
        },
    ]
);

registerWebsitePreviewTour(
    "seo_broken_links_stale",
    // The broken link and its French translation are set up server side.
    {},
    () => [
        ...mockLinkChecks(),
        ...openSeoModal(),
        {
            content: "Replace the broken link",
            trigger: `${brokenLinkRow("lien texte")} input.is-invalid`,
            run: "edit /contactus",
        },
        {
            content: "Check the new link",
            trigger: `${brokenLinkRow("lien texte")} button.btn-primary:enabled`,
            run: "click",
        },
        {
            content: "The new link is valid",
            trigger: `${brokenLinkRow("lien texte")} input.is-valid`,
        },
        {
            content: "Meanwhile, the link is fixed from another tab",
            // the page is behind the dialog, so it is not the trigger
            trigger: ".oe_seo_configuration",
            async run() {
                const linkEl = [...document.querySelectorAll("iframe")]
                    .map((iframe) => iframe.contentDocument?.querySelector("#wrap a[href='/broken-text']"))
                    .find(Boolean);
                const viewEl = linkEl.closest("[data-oe-model='ir.ui.view'][data-oe-id]");
                await rpc("/website/update_broken_links", {
                    links: [
                        {
                            oldLink: "/broken-text",
                            newLink: "/contactus?other_tab=1",
                            remove: false,
                            res_model: "ir.ui.view",
                            res_id: parseInt(viewEl.dataset.oeId),
                            field: "arch",
                        },
                    ],
                    lang: "fr_FR",
                });
            },
        },
        ...saveSeoModal(),
        {
            content: "The user is warned that the link was not found anymore",
            trigger: ".o_notification:contains('/broken-text')",
        },
        {
            content: "The link fixed from the other tab is kept",
            trigger: ":iframe #wrap a[href='/contactus?other_tab=1']:contains('lien texte')",
        },
    ]
);
