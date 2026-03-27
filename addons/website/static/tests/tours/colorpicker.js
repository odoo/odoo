import {
    insertSnippet,
    clickOnSave,
    clickOnEditAndWaitEditMode,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

function selectColorpickerSwitchPanel(type) {
    return [
        {
            content: "Select text snippet",
            trigger: ":iframe #wrap .s_text_block",
            run: "click",
        },
        {
            content: "Click on background-color option",
            trigger: "div[data-label='Background'] .o_we_color_preview[title='Color']",
            run: "click",
        },
        {
            content: "Select type of colorpicker in switch panel",
            trigger: `.o_popover .o_font_color_selector .btn-tab:contains("${type}")`,
            run: "click",
        },
    ];
}

function checkBackgroundColorWithHEX(hexCode) {
    return [
        {
            content: "Check if the RGBA color matches the selected color",
            trigger: ".o_popover .o_colorpicker_widget .o_hex_input",
            run: function () {
                const hex = this.anchor.value;
                if (hex !== hexCode) {
                    console.error("There may be a problem with the RGBA colorpicker");
                }
            },
        },
    ];
}

registerWebsitePreviewTour(
    "website_background_colorpicker",
    {
        edition: true,
        url: "/",
    },
    () => [
        ...insertSnippet({
            id: "s_text_block",
            name: "Text",
            groupName: "Text",
        }),
        ...selectColorpickerSwitchPanel("Gradient"),
        {
            content: "Select first gradient element",
            trigger:
                ".o_colorpicker_sections .o_color_button[data-color='linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)']",
            run: "click",
        },
        ...clickOnSave(),
        ...clickOnEditAndWaitEditMode(),
        ...selectColorpickerSwitchPanel("Gradient"),
        {
            content: "Click on custom button to open colorpicker widget",
            trigger:
                "button:contains('Custom')[style='background-image: linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%);']",
            run: "click",
        },
        ...checkBackgroundColorWithHEX("#FFCC33"),
        ...clickOnSave(),
        ...clickOnEditAndWaitEditMode(),
        ...selectColorpickerSwitchPanel("Custom"),
        {
            content: "Select first custom color element",
            trigger: ".o_colorpicker_section button[data-color='black']",
            run: "click",
        },
        ...clickOnSave(),
        ...clickOnEditAndWaitEditMode(),
        ...selectColorpickerSwitchPanel("Custom"),
        ...checkBackgroundColorWithHEX("#000000"),
    ]
);
