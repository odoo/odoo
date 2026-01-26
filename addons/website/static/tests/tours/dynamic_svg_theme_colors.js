import {
    changeOption,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const THEME_DOC = document.querySelector("iframe")?.contentDocument || document;
const THEME_STYLE = THEME_DOC.defaultView.getComputedStyle(THEME_DOC.documentElement);
const COLOR_1 = THEME_STYLE.getPropertyValue("--o-color-1");
const COLOR_2 = THEME_STYLE.getPropertyValue("--o-color-2");
const COLOR_3 = THEME_STYLE.getPropertyValue("--o-color-3");
const COLOR_1_ENC = encodeURIComponent(COLOR_1);
const COLOR_2_ENC = encodeURIComponent(COLOR_2);
const IMG_SELECTOR =
    ":iframe .s_text_image img[src^='/html_editor/shape/illustration/dynamic-svg-test']";
const IMG_SELECTOR_C1C2 = `${IMG_SELECTOR}[src*='c1=${COLOR_1_ENC}'][src*='c2=${COLOR_2_ENC}']`;
const IMG_SELECTOR_C3 = `${IMG_SELECTOR}[src*='c1=o-color-3'][src*='c2=${COLOR_2_ENC}']`;

async function assertSvgColors(img, color1, color2, errorMessage) {
    const response = await fetch(img.src);
    const svg = await response.text();
    if (!svg.includes(color1) || !svg.includes(color2) || !svg.includes("#000000")) {
        throw new Error(errorMessage);
    }
}

registerWebsitePreviewTour(
    "website_dynamic_svg_theme_colors",
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
            content: "Set the dynamic SVG image",
            trigger: ":iframe .s_text_image img",
            run() {
                this.anchor.setAttribute(
                    "src",
                    "/html_editor/shape/illustration/dynamic-svg-test" +
                        `?c1=${COLOR_1_ENC}&c2=${COLOR_2_ENC}&unique=4a2363`
                );
            },
        },
        {
            content: "Check the SVG uses theme colors",
            trigger: IMG_SELECTOR_C1C2,
            async run() {
                await assertSvgColors(
                    this.anchor,
                    COLOR_1,
                    COLOR_2,
                    "Dynamic SVG theme colors were not applied."
                );
            },
        },
        {
            content: "Select the dynamic SVG image",
            trigger: IMG_SELECTOR_C1C2,
            run: "click",
        },
        changeOption("Image", ".o_we_color_preview"),
        {
            content: "Select o-color-3 in the colorpicker",
            trigger: ".o_colorpicker_section button[data-color='o-color-3']",
            run: "click",
        },
        {
            content: "Check the SVG uses the new theme color",
            trigger: IMG_SELECTOR_C3,
            async run() {
                await assertSvgColors(
                    this.anchor,
                    COLOR_3,
                    COLOR_2,
                    "Dynamic SVG color did not update."
                );
            },
        },
        changeOption("Image", ".o_we_color_preview"),
        {
            content: "Reset the colorpicker",
            trigger: ".o_popover button[title='Reset']",
            run: "click",
        },
        {
            content: "Check the SVG uses the theme colors on reset",
            trigger: IMG_SELECTOR_C1C2,
            async run() {
                await assertSvgColors(
                    this.anchor,
                    COLOR_1,
                    COLOR_2,
                    "Dynamic SVG theme colors were not restored."
                );
            },
        },
    ]
);
