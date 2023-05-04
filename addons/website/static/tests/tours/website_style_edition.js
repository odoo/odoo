/** @odoo-module **/

import wTourUtils from "website.tour_utils";

const TARGET_FONT_SIZE = 30;

const checkFontSize = function () {
    const style = document.defaultView.getComputedStyle(this.$anchor[0]);
    if (style.fontSize !== `${TARGET_FONT_SIZE}px`) {
        console.error(`Expected the font-size to be equal to ${TARGET_FONT_SIZE}px but found ${style.fontSize} instead`);
    }
};

wTourUtils.registerWebsitePreviewTour("website_style_edition", {
    test: true,
    url: '/',
    edition: true,
}, [{
    content: "Go to theme options",
    trigger: '.o_we_customize_theme_btn',
}, {
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
},
...wTourUtils.clickOnSave(),
{
    content: "Check the font size is still ok outside of edit mode",
    trigger: 'iframe body:not(.editor_enable) #wrapwrap',
    run: checkFontSize,
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
