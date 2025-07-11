import {
    clickOnSave,
    clickOnSnippet,
    clickOnEditAndWaitEditMode,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

function selectColorpickerSwitchPanel(type, name) {
    return [
        {
            content: "Select map snippet",
            trigger: ":iframe #wrap .s_map",
            run: "click",
        },
        {
            content: `Click on ${type}-color option`,
            trigger: `div[data-label="${type} Color"] .o_we_color_preview`,
            run: "click",
        },
        {
            content: "Select type of colorpicker in switch panel",
            trigger: `.o_popover .o_font_color_selector .btn-tab:contains("${name}")`,
            run: "click",
        },
    ];
}

function changeColorWithHEX(hexCode) {
    return [
        {
            content: "Change color with  RGBA color using HEX input",
            trigger: ".o_popover .o_colorpicker_widget .o_hex_input",
            run: `edit #${hexCode} && click .o_color_picker_inputs`,
        },
    ];
}

registerWebsitePreviewTour(
    "snippet_map_description",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_map", name: "Map", groupName: "Social" }),
        ...clickOnSnippet({
            id: "s_map",
            name: "Map",
        }),
        {
            content: "Toggle the description",
            trigger: "div[data-action-id='mapDescription'] input[type='checkbox']",
            run: "click",
        },
        {
            content: "Check that the description is in the DOM",
            trigger: ":iframe .description",
        },
        {
            content: "Change the description text using the editor",
            trigger: "div[data-action-id='mapDescriptionTextValue'] input",
            run: "edit New description text",
        },
        {
            content: "check that the description text is in the DOM",
            trigger: ":iframe div.description:contains('New description text')",
        },
        ...selectColorpickerSwitchPanel("Background", "Gradient"),
        {
            content: "Select first gradient element",
            trigger:
                ".o_colorpicker_sections .o_color_button[data-color='linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)']",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Check that the Gradient Background Color is applied",
            trigger:
                ":iframe div.description[style='background-image: linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%);']",
        },
        ...clickOnEditAndWaitEditMode(),
        ...selectColorpickerSwitchPanel("Background", "Custom"),
        ...changeColorWithHEX("#E4F641"),
        ...clickOnSave(),
        {
            content: "Check that the custom Background Color is applied",
            trigger:
                ":iframe div.description[style='background-color: rgb(228, 246, 65) !important;']",
        },
        ...clickOnEditAndWaitEditMode(),
        ...selectColorpickerSwitchPanel("Text", "Custom"),
        ...changeColorWithHEX("#EB28EB"),
        ...clickOnSave(),
        {
            content: "Check that the Text Color is applied",
            trigger:
                ":iframe div.description[style='background-color: rgb(228, 246, 65) !important; color: rgb(235, 40, 235);']",
        },
    ]
);
