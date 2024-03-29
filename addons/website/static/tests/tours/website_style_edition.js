/** @odoo-module **/

import weUtils from "@web_editor/js/common/utils";
import wTourUtils from "@website/js/tours/tour_utils";

const TARGET_FONT_SIZE = 30;
const TARGET_BODY_BG_COLOR = '#00FF00';
const TARGET_BODY_BG_COLOR_V2 = 'rgb(0, 255, 0)';
const TARGET_BODY_COLOR = '#FF00FF';
const TARGET_BODY_COLOR_V2 = 'rgb(255, 0, 255)';

const checkFontSize = function () {
    const style = document.defaultView.getComputedStyle(this.$anchor[0]);
    if (!weUtils.areCssValuesEqual(style.fontSize, `${TARGET_FONT_SIZE}px`, 'font-size', this.$anchor)) {
        console.error(`Expected the font-size to be equal to ${TARGET_FONT_SIZE}px but found ${style.fontSize} instead`);
    }
};
const checkBodyBgColor = function () {
    const style = document.defaultView.getComputedStyle(this.$anchor[0]);
    if (!weUtils.areCssValuesEqual(style.backgroundColor, `${TARGET_BODY_BG_COLOR}`, 'background-color', this.$anchor)) {
        console.error(`Expected the background color to be equal to ${TARGET_BODY_BG_COLOR} but found ${style.backgroundColor} instead`);
    }
};
const checkBodyColor = function () {
    const style = document.defaultView.getComputedStyle(this.$anchor[0]);
    if (!weUtils.areCssValuesEqual(style.color, `${TARGET_BODY_COLOR}`, 'color', this.$anchor)) {
        console.error(`Expected the color to be equal to ${TARGET_BODY_COLOR} but found ${style.color} instead`);
    }
};

wTourUtils.registerWebsitePreviewTour("website_style_edition", {
    test: true,
    url: '/',
    edition: true,
}, () => [
wTourUtils.goToTheme(),
{
    content: "Change font size",
    trigger: '[data-variable="font-size-base"] input',
    run: `text_blur ${TARGET_FONT_SIZE}`,
}, {
    content: "Check the font size was properly adapted",
    trigger: 'iframe #wrapwrap',
    // Waiting the CSS to be reloaded: the code adds a new assets bundle with
    // a #t=... at the end then removes the old one.
    extra_trigger: 'iframe html:not(:has(link[href$="web.assets_frontend.min.css"]))',
    run: checkFontSize,
}, {
    content: "Open the color combinations area",
    trigger: '.o_we_theme_presets_collapse we-toggler',
}, {
    content: "Open a color combination",
    trigger: '.o_we_cc_preview_wrapper',
}, {
    content: "Edit the background color of that color combination",
    trigger: '.o_we_theme_presets_collapse we-collapse .o_we_so_color_palette:eq(0)',
}, {
    content: "Choose a color",
    trigger: `.o_we_color_btn[style*="background-color:${TARGET_BODY_BG_COLOR}"]`,
}, {
    content: "Check the body background color was properly adapted",
    trigger: 'iframe body',
    extra_trigger: `
        .o_we_theme_presets_collapse we-collapse .o_we_so_color_palette:eq(0) .o_we_color_preview[style*="${TARGET_BODY_BG_COLOR}"],
        .o_we_theme_presets_collapse we-collapse .o_we_so_color_palette:eq(0) .o_we_color_preview[style*="${TARGET_BODY_BG_COLOR_V2}"]
    `,
    run: checkBodyBgColor,
}, {
    content: "Edit the text color of that color combination",
    trigger: '.o_we_theme_presets_collapse we-collapse .o_we_so_color_palette:eq(1)',
}, {
    content: "Choose a color",
    trigger: `.o_we_color_btn[style*="background-color:${TARGET_BODY_COLOR}"]`,
}, {
    content: "Check the body color was properly adapted",
    trigger: 'iframe body',
    extra_trigger: `
        .o_we_theme_presets_collapse we-collapse .o_we_so_color_palette:eq(1) .o_we_color_preview[style*="${TARGET_BODY_COLOR}"],
        .o_we_theme_presets_collapse we-collapse .o_we_so_color_palette:eq(1) .o_we_color_preview[style*="${TARGET_BODY_COLOR_V2}"]
    `,
    run: checkBodyColor,
},
...wTourUtils.clickOnSave(),
{
    content: "Check the font size is still ok outside of edit mode",
    trigger: 'iframe body #wrapwrap',
    run: checkFontSize,
}, {
    content: "Check the body background color is still ok outside of edit mode",
    trigger: 'iframe body',
    run: checkBodyBgColor,
}, {
    content: "Check the body color is still ok outside of edit mode",
    trigger: 'iframe body',
    run: checkBodyColor,
},
...wTourUtils.clickOnEditAndWaitEditMode(),
wTourUtils.goToTheme(),
{
    content: "Click on the Background Image selection",
    trigger: '[data-customize-body-bg-type="\'image\'"]:not(.active)',
    extra_trigger: '[data-customize-body-bg-type="NONE"].active',
}, {
    content: "The media dialog should open",
    trigger: '.o_select_media_dialog',
    run: () => {}, // It's a check.
}]);
