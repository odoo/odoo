/** @odoo-module **/

import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const CUSTOM_COLOR_1 = "#ABCDEF"; // foreground
const CUSTOM_COLOR_2 = "#654321"; // background

registerWebsitePreviewTour(
    "website_custom_colors_picking",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_text_block",
            name: "Text",
            groupName: "Text",
        }),
        {
            content: "Click on the text block first paragraph",
            trigger: ":iframe .s_text_block p",
            run: "click",
        },
        {
            content: "Open the foreground colorpicker",
            trigger: "#toolbar:not(.oe-floating) #oe-text-color",
            run: "click",
        },
        {
            content: "Go to the 'Custom' tab",
            trigger: '.o_we_colorpicker_switch_pane_btn[data-target="custom-colors"]',
            run: "click",
        },
        {
            content: "Input the custom color 1",
            trigger: ".o_hex_input",
            run: `edit ${CUSTOM_COLOR_1}`,
        },
        {
            content: "Open the background colorpicker",
            trigger: '.o_we_user_value_widget[data-color-prefix="bg-"]',
            run: "click",
        },
        {
            content: "Go to the 'Custom' tab",
            trigger: '.o_we_colorpicker_switch_pane_btn[data-target="custom-colors"]',
            run: "click",
        },
        {
            content: "Input the custom color 2",
            trigger: ".o_hex_input",
            run: `edit ${CUSTOM_COLOR_2}`,
        },
        ...clickOnSave(),
        ...clickOnEditAndWaitEditMode(),
        ...insertSnippet({
            id: "s_title",
            name: "Title",
            groupName: "Text",
        }),
        {
            content: "Click on the text of the title block",
            trigger: ":iframe .s_title h2",
            run: "click",
        },
        {
            content: "Open the foreground colorpicker",
            trigger: "#toolbar:not(.oe-floating) #oe-text-color",
            run: "click",
        },
        {
            content: "Go to the 'Custom' tab",
            trigger: '.o_we_colorpicker_switch_pane_btn[data-target="custom-colors"]',
            run: "click",
        },
        {
            content: "Check if the custom color 1 & 2 can be applied (foreground)",
            trigger: ".dropdown-menu.colorpicker-menu.show .colorpicker",
            run: function (actions) {
                const customColorButton1 = this.anchor.querySelector(
                    `button[style="background-color:${CUSTOM_COLOR_1};"]`
                );
                if (!customColorButton1) {
                    throw new Error(
                        "The custom color button for the color 1 is missing for foreground colorpicker"
                    );
                }
                const customColorButton2 = this.anchor.querySelector(
                    `button[style="background-color:${CUSTOM_COLOR_2};"]`
                );
                if (!customColorButton2) {
                    throw new Error(
                        "The custom color button for the color 2 is missing for foreground colorpicker"
                    );
                }
            },
        },
        {
            content: "Open the background colorpicker",
            trigger: '.o_we_user_value_widget[data-color-prefix="bg-"]',
            run: "click",
        },
        {
            content: "Go to the 'Custom' tab",
            trigger: '.o_we_colorpicker_switch_pane_btn[data-target="custom-colors"]',
            run: "click",
        },
        {
            content: "Check if the custom color 1 & 2 can be applied (background)",
            trigger:
                ".o_we_user_value_widget.o_we_so_color_palette.o_we_widget_opened .colorpicker",
            run: function (actions) {
                const customColorButton1 = this.anchor.querySelector(
                    `button[style="background-color:${CUSTOM_COLOR_1};"]`
                );
                if (!customColorButton1) {
                    throw new Error(
                        "The custom color button for the color 1 is missing for background colorpicker"
                    );
                }
                const customColorButton2 = this.anchor.querySelector(
                    `button[style="background-color:${CUSTOM_COLOR_2};"]`
                );
                if (!customColorButton2) {
                    throw new Error(
                        "The custom color button for the color 2 is missing for background colorpicker"
                    );
                }
            },
        },
    ]
);
