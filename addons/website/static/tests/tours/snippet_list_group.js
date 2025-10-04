import {
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

function openColorPickerCustomTab(label) {
    return [
        {
            content: "Open the color picker for icon color",
            trigger: `div[data-container-title='List Group'] div[data-label='${label}'] .o_we_color_preview`,
            run: "click",
        },
        {
            content: "Switch to the Custom tab in the color picker",
            trigger: ".o_font_color_selector button:contains('Custom')",
            run: "click",
        },
    ];
}

function getBeforeProperty(el, prop) {
    return getComputedStyle(el, "::before").getPropertyValue(prop).trim();
}

registerWebsitePreviewTour(
    "snippet_list_group",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_list_group", name: "List Group" }),
        ...clickOnSnippet({ id: "s_list_group", name: "List Group" }),
        ...openColorPickerCustomTab("Color"),
        {
            content: "Select black color for the icon",
            trigger: ".o_color_picker_button[data-color='black']",
            run: "click",
        },
        {
            content: "Check that the icon color is black",
            trigger: ":iframe .s_list_group li",
            run() {
                const color = getBeforeProperty(this.anchor, "--icon-color");
                if (color !== "#000000") {
                    throw new Error(`Icon color is expected to be black but got ${color}`);
                }
            },
        },
        ...openColorPickerCustomTab("Background"),
        {
            content: "Select grey background color for the icon",
            trigger: ".o_color_picker_button[data-color='400']",
            run: "click",
        },
        {
            content: "Check that the icon background color is grey",
            trigger: ":iframe .s_list_group li",
            run() {
                const color = getBeforeProperty(this.anchor, "--icon-bg");
                if (color !== "#CED4DA") {
                    throw new Error(
                        `Icon background color is expected to be grey but got ${color}`
                    );
                }
            },
        },
        {
            content: "Click the Replace button to change icons",
            trigger: "button[data-action-id='replaceListIcon']",
            run: "click",
        },
        {
            content: "Select the star icon",
            trigger: ".font-icons-icons .fa-music",
            run: "click",
        },
        {
            content: "Check that the icon has changed to a music",
            trigger: ":iframe .s_list_group li",
            run() {
                const unicode = getBeforeProperty(this.anchor, "--icon-content");
                if (unicode !== '""') {
                    throw new Error(`Icon content is expected to be music but got ${unicode}`);
                }
            },
        },
    ]
);
