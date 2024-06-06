/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("translate_text_options", {
    url: "/",
    test: true,
}, () => [
    {
        content: "Change the language to English",
        trigger: "iframe .js_language_selector .js_change_lang[data-url_code=\"en\"]",
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.dragNDrop({
        id: "s_text_block",
        name: "Text",
    }),
    {
        content: "Select snippet first Text Block",
        trigger: "iframe .s_text_block p:first",
        run: "dblclick",
    },
    {
        content: "Click on the 'Animate Text' button to activate the option",
        trigger: "div.o_we_animate_text",
    },
    ...wTourUtils.clickOnSave(),
    ...wTourUtils.enterTranslateMode("fr"),
    ...wTourUtils.selectAndClick("snippet first Text Block (w/ animation on it)", "iframe .s_text_block p:first span span"),
    {
        content: "Check that the animation widget option menu is displayed",
        trigger: ".o_we_toolbar_wrapper #toolbar we-customizeblock-option.snippet-option-WebsiteAnimate",
        isCheck: true,
    },
    ...wTourUtils.selectAndClick("snippet last Text Block (has no animation)", "iframe .s_text_block p:last span"),
    {
        content: "Check that the animation widget option menu is not displayed",
        trigger: ".o_we_toolbar_wrapper #toolbar :not(we-customizeblock-option.snippet-option-WebsiteAnimate)",
        isCheck: true,
    },
    ...wTourUtils.selectAndClick("snippet first Text Block (w/ animation on it)", "iframe .s_text_block p:first span span"),
    {
        content: "Check that the animation widget option menu is also re displayed",
        trigger: ".o_we_toolbar_wrapper #toolbar we-customizeblock-option.snippet-option-WebsiteAnimate",
        isCheck: true,
    },
    ...wTourUtils.clickOnSave(),
]);
