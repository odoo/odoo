import {
    changeBackgroundColor,
    clickOnEditAndWaitEditMode,
    clickOnSave,
    clickOnSnippet,
    goToTheme,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const gradients = [
    "linear-gradient(135deg, rgb(203, 94, 238) 0%, rgb(75, 225, 236) 100%)",
    "linear-gradient(135deg, rgb(255, 222, 202) 0%, rgb(202, 115, 69) 100%)",
    "linear-gradient(135deg, rgb(47, 128, 237) 0%, rgb(178, 255, 218) 100%)",
];

const customColors = {
    header: { hex: "#B18AA7", rgb: "rgb(177, 138, 167)" },
    footer: { hex: "#65435C", rgb: "rgb(101, 67, 92)" },
};

const TARGETS = {
    cc: "color-combinations",
    bg: "custom-colors",
    gradients: "gradients",
};

const NAMES = {
    cc: "color combinations",
    bg: "background colors",
    gradients: "gradients",
};

function switchTo(type) {
    return {
        trigger: `.o_we_colorpicker_switch_pane_btn[data-target="${TARGETS[type]}"]`,
        content: `Switch to ${NAMES[type]}`,
        run: "click",
    };
}

function waitForIframeLoading() {
    return [
        {
            content: "Wait for iframe loading to start",
            trigger: ":iframe body:has(.o_we_ui_loading)",
        },
        {
            content: "Wait for iframe loading to finish",
            trigger: ":iframe body:not(:has(.o_we_ui_loading))",
        },
    ];
}

function getElementSelector(elementId) {
    return elementId === "o_header_standard" ? " nav" : "";
}

function getDataColorAttribute(elementId) {
    return elementId === "o_footer" ? "footer" : "menu";
}

function setupColorCombination() {
    return [
        ...goToTheme(),
        {
            content: "Open the color combinations area",
            trigger: ".o_we_theme_presets_collapse we-toggler",
            run: "click",
        },
        {
            content: "Open color combination 1",
            trigger: ".o_we_collapse_toggler.o_cc1",
            run: "click",
        },
        {
            content: "Edit the background color of color combination 1",
            trigger:
                "we-collapse.active:not(.o_we_theme_presets_collapse) .o_we_so_color_palette[data-layer-color='o-cc1-bg']",
            run: "click",
        },
        switchTo("gradients"),
        {
            trigger: ".o_we_colorpicker_switch_pane_btn.active[data-target='gradients']",
            content: "Verify switch to gradients",
        },
        {
            content: "Choose a gradient",
            trigger: `.o_we_color_btn[style*="background-image: ${gradients[0]}"]`,
            run: "click",
        },
        {
            trigger: `.o_we_so_color_palette[data-layer-color="o-cc1-bg"] .o_we_color_preview[style='background-image: ${gradients[0]};']`,
            content: "Verify gradient is selected",
        },
        {
            content: "Verify if gradient is applied",
            trigger: `.o_we_theme_presets_collapse .o_we_cc_preview_wrapper.o_cc1`,
            run() {
                const bgImage = getComputedStyle(this.anchor)["background-image"];
                if (!bgImage.includes(gradients[0])) {
                    throw new Error("Gradient background was NOT applied!");
                }
            },
        },
    ];
}

function openColorPicker(elementId, elementName) {
    return [
        ...clickOnSnippet({ id: elementId, name: elementName }),
        {
            trigger: ".o_we_customize_snippet_btn.active",
            content: "Make sure the customization tab is active",
        },
        changeBackgroundColor(),
        {
            trigger: ".o_we_so_color_palette.o_we_widget_opened",
            content: "Verify color picker is opened",
        },
    ];
}

function verifyBackgroundStyle(elementId, expectedBgColor, expectedBgImage, errorMessage) {
    return {
        trigger: `:iframe .${elementId}${getElementSelector(elementId)}`,
        content: `Verify ${errorMessage.toLowerCase()}`,
        run() {
            const bgColor = getComputedStyle(this.anchor)["background-color"];
            const bgImage = getComputedStyle(this.anchor)["background-image"];

            if (expectedBgColor && bgColor !== expectedBgColor) {
                throw new Error(
                    `${errorMessage} - Expected color: ${expectedBgColor}, got: ${bgColor}`
                );
            }
            if (expectedBgImage !== undefined && bgImage !== expectedBgImage) {
                throw new Error(
                    `${errorMessage} - Expected image: ${expectedBgImage}, got: ${bgImage}`
                );
            }
        },
    };
}

function applyAndVerifyGradient(elementId, elementName, gradientIndex) {
    const dataColorAttr = getDataColorAttribute(elementId);

    return [
        ...openColorPicker(elementId, elementName),
        switchTo("gradients"),
        {
            trigger: ".o_we_colorpicker_switch_pane_btn.active[data-target='gradients']",
            content: "Verify switch to gradients",
        },
        {
            trigger: `.o_we_color_btn[style*="background-image: ${gradients[gradientIndex]}"]`,
            content: `Choose gradient ${gradientIndex}`,
            run: "click",
        },
        {
            trigger: `.o_we_so_color_palette[data-color=${dataColorAttr}] .o_we_color_preview[style='background-color: var(--we-cp-o-cc1-bg); background-image: ${gradients[gradientIndex]};']`,
            content: "Verify gradient is selected in picker",
        },
        {
            trigger: `:iframe .${elementId}${getElementSelector(elementId)}`,
            content: "Verify gradient background is applied",
            run() {
                const bgImage = getComputedStyle(this.anchor)["background-image"];
                if (!bgImage.includes(gradients[gradientIndex])) {
                    throw new Error(`Gradient ${gradientIndex} was NOT applied!`);
                }
            },
        },
    ];
}

function applyAndVerifyCustomColor(elementId, elementName, colorConfig) {
    const dataColorAttr = getDataColorAttribute(elementId);

    return [
        ...openColorPicker(elementId, elementName),
        switchTo("bg"),
        {
            trigger: ".o_we_colorpicker_switch_pane_btn.active[data-target='custom-colors']",
            content: "Verify switch to custom colors",
        },
        {
            trigger: `.o_we_color_btn[style*='background-color:${colorConfig.hex}']`,
            content: "Choose a custom color",
            run: "click",
        },
        {
            trigger: `.o_we_so_color_palette[data-color=${dataColorAttr}] .o_we_color_preview[style='background-color: ${colorConfig.rgb}; background-image: none;']`,
            content: "Verify custom color is selected in picker",
        },
        verifyBackgroundStyle(
            elementId,
            colorConfig.rgb,
            "none",
            "Custom background color was NOT applied!"
        ),
    ];
}

function resetAndVerifyBackground(elementId, elementName) {
    return [
        ...openColorPicker(elementId, elementName),
        {
            trigger:
                ".o_we_color_palette_wrapper .o_we_colorpicker_switch_panel .o_colorpicker_reset",
            content: "Click on the None button of the color palette",
            run: "click",
        },
        ...waitForIframeLoading(),
        {
            trigger: `:iframe .${elementId}:not([style*="background-image"]):not([style*="background-color"])`,
            content: "All color classes and properties should have been removed",
        },
    ];
}

function applyColorCombination(elementId, elementName) {
    const dataColorAttr = getDataColorAttribute(elementId);

    return [
        ...openColorPicker(elementId, elementName),
        {
            trigger: `.o_we_color_btn[data-color='1']`,
            content: `Choose color combination 1`,
            run: "click",
        },
        {
            trigger: `.o_we_so_color_palette[data-color=${dataColorAttr}] .o_we_color_preview[style="background-color: var(--we-cp-o-cc1-bg); background-image: var(--we-cp-o-cc1-bg-gradient);"]`,
            content: "Verify color combination is selected in picker",
        },
        {
            trigger: `:iframe .${elementId}${getElementSelector(elementId)}`,
            content: "Verify color combination is applied",
            run() {
                const bgColor = getComputedStyle(this.anchor)["background-color"];
                const bgImage = getComputedStyle(this.anchor)["background-image"];
                if (bgColor !== "rgba(0, 0, 0, 0)" || bgImage === "none") {
                    throw new Error("Color combination was NOT applied!");
                }
            },
        },
    ];
}

function createElementTestSequence(elementId, elementName, gradientIndex, colorConfig) {
    return [
        ...resetAndVerifyBackground(elementId, elementName),
        ...applyColorCombination(elementId, elementName),
        ...applyAndVerifyGradient(elementId, elementName, gradientIndex),
        ...applyAndVerifyCustomColor(elementId, elementName, colorConfig),
    ];
}

registerWebsitePreviewTour(
    "background_color_gradient_precedence",
    {
        url: "/",
        edition: true,
    },
    () => [
        // Configure color combinations with gradients
        ...setupColorCombination(),

        // Header
        ...createElementTestSequence("o_header_standard", "Header", 1, customColors.header),
        ...clickOnSave(),
        ...clickOnEditAndWaitEditMode(),

        // Footer
        ...createElementTestSequence("o_footer", "Footer", 2, customColors.footer),
    ]
);
