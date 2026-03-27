import {
    insertSnippet,
    goBackToBlocks,
    goToTheme,
    registerWebsitePreviewTour,
    clickToolbarButton,
} from "@website/js/tours/tour_utils";
import { rgbToHex } from "@web/core/utils/colors";

const WEBSITE_MAIN_COLOR = "#ABCDEF";

registerWebsitePreviewTour(
    "website_text_edition",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...goToTheme(),
        {
            content: "Open colorpicker to change website main color",
            trigger: ".we-bg-options-container .o_we_color_preview",
            run: "click",
        },
        {
            content: "Open colorpicker to change website main color",
            trigger: ".o_font_color_selector button:contains('Custom')",
            run: "click",
        },
        {
            content:
                "Input the value for the new website main color (also make sure it is independent from the backend)",
            trigger: ".o_hex_input",
            run: `edit ${WEBSITE_MAIN_COLOR} && click body`,
        },
        goBackToBlocks(),
        ...insertSnippet({ id: "s_text_block", name: "Text", groupName: "Text" }),
        ...clickToolbarButton(
            "text block first paragraph",
            ".s_text_block p",
            "Apply Font Color",
            true
        ),
        {
            content: "Open solid section in color picker",
            trigger: ".o_font_color_selector button:contains('Custom')",
            run: "click",
        },
        {
            content: "Select main color",
            trigger: ".o_colorpicker_widget .o_color_picker_inputs .o_hex_input",
            run: `edit ${WEBSITE_MAIN_COLOR} && click body`,
        },
        {
            content: "Check that paragraph now uses the main color *class*",
            trigger: ":iframe .s_text_block p",
            run: function (actions) {
                const fontEl = this.anchor.querySelector("font");
                if (!fontEl) {
                    console.error("A background color should have been applied");
                    return;
                }
                if (fontEl.style.backgroundColor) {
                    console.error("The paragraph should not have an inline style background color");
                    return;
                }
                const rgbColor = fontEl.style.getPropertyValue("color");
                const hexColor = rgbToHex(rgbColor);
                if (hexColor.toUpperCase() !== WEBSITE_MAIN_COLOR) {
                    console.error("The paragraph should have the right background color class");
                    return;
                }
            },
        },
    ]
);
