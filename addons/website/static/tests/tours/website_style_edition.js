import { areCssValuesEqual } from "@html_builder/utils/utils_css";
import {
    changeOptionInPopover,
    clickOnEditAndWaitEditMode,
    clickOnSave,
    goToTheme,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const TARGET_FONT_SIZE = 20; // The max to not be impacted by the responsive font size system
const TARGET_BODY_BG_COLOR = "#00FF00";
const TARGET_BODY_BG_COLOR_V2 = "rgb(0, 255, 0)";
const TARGET_BODY_COLOR = "#FF00FF";
const TARGET_BODY_COLOR_V2 = "rgb(255, 0, 255)";

const checkFontSize = function () {
    const style = document.defaultView.getComputedStyle(this.anchor);
    if (!areCssValuesEqual(style.fontSize, `${TARGET_FONT_SIZE}px`, "font-size", style)) {
        console.error(
            `Expected the font-size to be equal to ${TARGET_FONT_SIZE}px but found ${style.fontSize} instead`
        );
    }
};
const checkBodyBgColor = function () {
    const style = document.defaultView.getComputedStyle(this.anchor);
    if (
        !areCssValuesEqual(
            style.backgroundColor,
            `${TARGET_BODY_BG_COLOR}`,
            "background-color",
            style
        )
    ) {
        console.error(
            `Expected the background color to be equal to ${TARGET_BODY_BG_COLOR} but found ${style.backgroundColor} instead`
        );
    }
};
const checkBodyColor = function () {
    const style = document.defaultView.getComputedStyle(this.anchor);
    if (!areCssValuesEqual(style.color, `${TARGET_BODY_COLOR}`, "color", style)) {
        console.error(
            `Expected the color to be equal to ${TARGET_BODY_COLOR} but found ${style.color} instead`
        );
    }
};

registerWebsitePreviewTour(
    "website_style_edition",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...goToTheme(),
        {
            content: "Change font size",
            trigger: "[data-action-param='font-size-base'] input",
            run: `edit ${TARGET_FONT_SIZE} && click body`,
        },
        {
            // Waiting the CSS to be reloaded: the code adds a new assets bundle
            // with a #t=... at the end then removes the old one.
            trigger: ':iframe html:not(:has(link[href$="web.assets_frontend.min.css"]))',
        },
        {
            content: "Check the font size was properly adapted",
            trigger: ":iframe #wrapwrap",
            run: checkFontSize,
        },
        {
            content: "Open the theme color slider",
            trigger: "button.o-hb-theme-color-slider-btn",
            run: "click",
        },
        {
            content: "Open a color combination",
            trigger: "div[data-container-title='Color Presets'] button.o_hb_collapse_toggler",
            run: "click",
        },
        {
            content: "Edit the background color of that color combination",
            trigger: "div[id^='builder_collapse_content'] div .o_we_color_preview",
            run: "click",
        },
        {
            content: "Choose a color",
            trigger: `.o_font_color_selector .o_color_button[data-color="${TARGET_BODY_BG_COLOR}"]`,
            run: "click",
        },
        {
            trigger: `
        div[id^='builder_collapse_content'] div .o_we_color_preview[style*="${TARGET_BODY_BG_COLOR}"],
        div[id^='builder_collapse_content'] div .o_we_color_preview[style*="${TARGET_BODY_BG_COLOR_V2}"]
    `,
        },
        {
            content: "Check the body background color was properly adapted",
            trigger: ":iframe body",
            run: checkBodyBgColor,
        },
        {
            content: "Edit the text color of that color combination",
            trigger:
                "div[id^='builder_collapse_content'] div[data-label='Text'] .o_we_color_preview",
            run: "click",
        },
        {
            content: "Choose a color",
            trigger: `.o_font_color_selector .o_color_button[data-color="${TARGET_BODY_COLOR}"]`,
            run: "click",
        },
        {
            trigger: `
        div[id^='builder_collapse_content'] div .o_we_color_preview[style*="${TARGET_BODY_COLOR}"],
        div[id^='builder_collapse_content'] div .o_we_color_preview[style*="${TARGET_BODY_COLOR_V2}"]
    `,
        },
        {
            content: "Check the body color was properly adapted",
            trigger: ":iframe body",
            run: checkBodyColor,
        },
        ...clickOnSave(),
        {
            content: "Check the font size is still ok outside of edit mode",
            trigger: ":iframe body #wrapwrap",
            run: checkFontSize,
        },
        {
            content: "Check the body background color is still ok outside of edit mode",
            trigger: ":iframe body",
            run: checkBodyBgColor,
        },
        {
            content: "Check the body color is still ok outside of edit mode",
            trigger: ":iframe body",
            run: checkBodyColor,
        },
        ...clickOnEditAndWaitEditMode(),
        ...goToTheme(),
        ...changeOptionInPopover("Website", "Page Layout", "Boxed"),
        {
            content: "Wait for the background color picker",
            trigger: "[data-label='Background'] button.o_we_color_preview",
        },
        {
            content: "Add a body background image",
            trigger:
                "div[data-label='Page Layout'] button[data-action-id='toggleBodyBgImage']:not(.active)",
            run: "click",
        },
        {
            content: "Pick the test image",
            trigger: ".o_select_media_dialog .o_button_area[aria-label='bg_test.png']",
            run: "click",
        },
        {
            content: "Wait for image options to be visible",
            trigger:
                ".o_theme_tab button[data-action-id='replaceBodyBgImage'], .o_theme_tab button[data-action-id='removeBodyBgImage']",
        },
        ...changeOptionInPopover("Website", "Position", "Repeat pattern"),
        {
            content: "Set pattern width",
            trigger: ".o_theme_tab [data-action-param='body-image-pattern-width'] > input",
            run: "edit 123 && click body",
        },
        {
            content: "Ensure pattern width applied",
            trigger: ":iframe #wrapwrap",
            async run({ anchor, waitUntil }) {
                let size = "";
                try {
                    await waitUntil(
                        () => {
                            size = getComputedStyle(anchor).backgroundSize;
                            return size.includes("123px");
                        },
                        {
                            timeout: 8000,
                        }
                    );
                } catch {
                    throw new Error(`Expected background-size width to be 123px, got ${size}`);
                }
            },
        },
        {
            content: "Set pattern height",
            trigger: ".o_theme_tab [data-action-param='body-image-pattern-height'] > input",
            run: "edit 77 && click body",
        },
        {
            content: "Ensure pattern size applied",
            trigger: ":iframe #wrapwrap",
            async run({ anchor, waitUntil }) {
                let size = "";
                try {
                    await waitUntil(
                        () => {
                            size = getComputedStyle(anchor).backgroundSize;
                            return size.includes("123px") && size.includes("77px");
                        },
                        {
                            timeout: 8000,
                        }
                    );
                } catch {
                    throw new Error(
                        `Expected background-size to include 123px and 77px, got ${size}`
                    );
                }
            },
        },
        {
            content: "Remove the body background image",
            trigger: ".o_theme_tab button[data-action-id='removeBodyBgImage']",
            run: "click",
        },
        {
            content: "Image controls should be hidden",
            trigger: ".o_theme_tab :not(:has(button[data-action-id='replaceBodyBgImage'])",
        },
    ]
);
