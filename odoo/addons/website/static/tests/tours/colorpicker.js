/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

function selectColorpickerSwitchPanel(type) {
    return [
        {
            content: "Select text snippet",
            trigger: "iframe #wrap .s_text_block",
        },
        {
            content: "Click on background-color option",
            trigger: ".o_we_so_color_palette[data-css-property='background-color']",
        },
        {
            content: "Select type of colorpicker in switch panel",
            trigger: `.o_we_colorpicker_switch_pane_btn[data-target="${type}"]`,
        },
    ]
}

function checkBackgroundColorWithRGBA(red, green, blue) {
    return [
        {
            content: "Check if the RGBA color matches the selected color",
            trigger: ".o_rgba_div",
            run: ({ tip_widget }) => {
                const rgbaEl = tip_widget.$anchor[0];
                const red_color = rgbaEl.querySelector(".o_red_input").value;
                const green_color = rgbaEl.querySelector(".o_green_input").value;
                const blue_color = rgbaEl.querySelector(".o_blue_input").value;
                if (red_color != red || green_color != green || blue_color != blue) {
                    console.error("There may be a problem with the RGBA colorpicker");
                }
            }
        },
    ]
}

wTourUtils.registerWebsitePreviewTour("website_background_colorpicker", {
    test: true,
    edition: true,
    url: "/",
}, () => [
    wTourUtils.dragNDrop({
        id: "s_text_block",
        name: "Text",
    }),
    ...selectColorpickerSwitchPanel("gradients"),
    {
        content: "Select first gradient element",
        trigger: ".o_colorpicker_section .o_we_color_btn[data-color='linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)']",
    },
    ...wTourUtils.clickOnSave(),
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    ...selectColorpickerSwitchPanel("gradients"),
    ...checkBackgroundColorWithRGBA("255", "204", "51"),
    ...wTourUtils.clickOnSave(),
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    ...selectColorpickerSwitchPanel("custom-colors"),
    {
        content: "Select first custom color element",
        trigger: ".o_colorpicker_section .o_we_color_btn[style='background-color:#65435C;']",
    },
    ...wTourUtils.clickOnSave(),
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    ...selectColorpickerSwitchPanel("custom-colors"),
    ...checkBackgroundColorWithRGBA("101", "67", "92"),
]);
