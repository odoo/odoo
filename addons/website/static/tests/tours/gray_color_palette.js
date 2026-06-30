import { goToTheme, registerWebsitePreviewTour, clickOnSave } from "@website/js/tours/tour_utils";

function waitForCSSReload() {
    return [
        {
            content: "Wait for no loading",
            trigger: "body:not(:has(.o_we_ui_loading)) :iframe body:not(:has(.o_we_ui_loading))",
        },
    ];
}

registerWebsitePreviewTour(
    "website_gray_color_palette",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...goToTheme(),
        {
            content: "Toggle gray color palette",
            trigger: ".we-bg-options-container [data-label=Grays] div",
            run: "click",
        },
        {
            content: "Drag the hue slider",
            trigger: ".o_we_slider_tint [data-action-param=gray-hue] input",
            run: "range 100",
        },
        ...waitForCSSReload(),
        {
            content: "Check the preview of the gray 900 after hue change",
            trigger:
                ".o_we_gray_preview span[variable='900'][style='background-color: #242921 !important']",
        },
        {
            content: "Drag the saturation slider",
            trigger: "div[data-action-param=gray-extra-saturation] input",
            run: "range 15",
        },
        ...waitForCSSReload(),
        {
            content: "Check the preview of the gray 900 after saturation change",
            trigger:
                ".o_we_gray_preview span[variable='900'][style='background-color: #222F1B !important']",
        },
        ...clickOnSave(),
        {
            content: "Check value of the gray 900 color",
            trigger: ":iframe #wrapwrap:not(.odoo-editor-editable)",
            run() {
                const iframeEl = document.querySelector(".o_website_preview iframe");
                const styles = getComputedStyle(iframeEl.contentDocument.documentElement);
                if (styles.getPropertyValue("--900").trim() !== "#222F1B") {
                    throw new Error("The value for the gray 900 is not right");
                }
            },
        },
    ]
);
