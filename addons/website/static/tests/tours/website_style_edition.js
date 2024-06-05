odoo.define("website.tour.website_style_edition", function (require) {
"use strict";

const tour = require("web_tour.tour");

const TARGET_FONT_SIZE = 30;
const TARGET_PRIMARY_COLOR_INPUT = "#ff0000";
const TARGET_PRIMARY_COLOR_RESULT = "rgb(255, 0, 0)";

tour.register("website_style_edition", {
    test: true,
    url: "/",
}, [{
    content: "Enter edit mode",
    trigger: 'a[data-action=edit]',
}, {
    content: "Go to theme options",
    trigger: '.o_we_customize_theme_btn',
}, {
    content: "Change font size",
    trigger: '[data-variable="font-size-base"] input',
    run: `text_blur ${TARGET_FONT_SIZE}`,
}, {
    content: "Save",
    trigger: '[data-action="save"]',
}, {
    content: "Check the font size was properly adapted",
    trigger: 'body:not(.editor_enable) #wrapwrap',
    run: function (actions) {
        const style = window.getComputedStyle(this.$anchor[0]);
        if (style.fontSize !== `${TARGET_FONT_SIZE}px`) {
            console.error(`Expected the font-size to be equal to ${TARGET_FONT_SIZE}px but found ${style.fontSize} instead`);
        }
    },
}, {
    content: "Enter edit mode",
    trigger: 'a[data-action=edit]',
}, {
    content: "Go to theme options",
    trigger: '.o_we_customize_theme_btn',
}, {
    content: "Open primary color colorpicker",
    trigger: '[data-color="o-color-1"]',
}, {
    content: "Pick custom color without closing the picker",
    trigger: '[data-color="o-color-1"] .o_hex_input',
    run: `text_blur ${TARGET_PRIMARY_COLOR_INPUT}`,
}, {
    content: "Save",
    trigger: '[data-action="save"]',
}, {
    content: "Check the color was saved",
    trigger: 'body:not(.editor_enable) .btn-primary',
    run: function (actions) {
        const style = window.getComputedStyle(this.$anchor[0]);
        if (style.backgroundColor !== `${TARGET_PRIMARY_COLOR_RESULT}`) {
            console.error(`Expected the primary color to be equal to ${TARGET_PRIMARY_COLOR_RESULT} but found ${style.backgroundColor} instead`);
        }
    },
}]);
});
