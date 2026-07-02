import { registry } from "@web/core/registry";
import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    selectHeader,
    waitForEditMode,
} from "@website/js/tours/tour_utils";

const headerBlurRangeSelector =
    "[data-container-title='Header'] [data-label='Blur'] input[type='range']";

function setHeaderBackgroundHex(hexColor) {
    return [
        selectHeader(),
        {
            content: "Open the header background color picker",
            trigger:
                "div[data-container-title='Header'] [data-label='Background'] .o_we_color_preview",
            run: "click",
        },
        {
            content: "Switch to custom colors",
            trigger: ".o-hb-colorpicker .custom-tab",
            run: "click",
        },
        {
            content: `Set header background to ${hexColor}`,
            trigger: ".o_color_picker_inputs :iframe input",
            run: `edit ${hexColor} && click body`,
        },
        {
            content: "Wait for the operation to finish",
            trigger: ".o_website_preview :iframe:not(:has(.o_loading_screen))",
        },
    ];
}

function checkHeaderBlurValue(expectedValue) {
    return {
        content: `Check that --o-bg-blur is ${expectedValue}`,
        trigger: ":iframe #wrapwrap > header nav",
        async run({ waitUntil }) {
            await waitUntil(
                () => {
                    const blurValue = getComputedStyle(this.anchor).getPropertyValue("--o-bg-blur");
                    return parseFloat(blurValue) === expectedValue;
                },
                {
                    message: `Expected --o-bg-blur to be ${expectedValue}.}`,
                }
            );
        },
    };
}

registry.category("web_tour.tours").add("header_bg_blur_option", {
    steps: () => [
        waitForEditMode,
        selectHeader(),
        {
            content: "Check that the blur option is hidden for opaque backgrounds",
            trigger: `:not(${headerBlurRangeSelector})`,
        },

        ...setHeaderBackgroundHex("#00000080"),
        {
            content: "Check that the blur option appears for transparent backgrounds",
            trigger: headerBlurRangeSelector,
        },
        {
            content: "Set the header blur to 5",
            trigger: headerBlurRangeSelector,
            run: "range 5",
        },
        {
            content: "Wait for the operation to finish",
            trigger: ".o_website_preview :iframe:not(:has(.o_loading_screen))",
        },
        checkHeaderBlurValue(5),
        ...clickOnSave(),
        checkHeaderBlurValue(5),

        ...clickOnEditAndWaitEditMode(),
        ...setHeaderBackgroundHex("#000000"),
        {
            content: "Check that the blur option is hidden again",
            trigger: `:not(${headerBlurRangeSelector})`,
        },
        checkHeaderBlurValue(0),
        selectHeader(),
        {
            content: "Open the header background color picker",
            trigger:
                "div[data-container-title='Header'] [data-label='Background'] .o_we_color_preview",
            run: "click",
        },
        {
            content: "Switch to gradient colors",
            trigger: ".o-hb-colorpicker .gradient-tab",
            run: "click",
        },
        {
            content: "Open the custom gradient editor",
            trigger: ".o_popover .o_custom_gradient_button",
            run: "click",
        },
        {
            content: "Set a transparent gradient stop",
            trigger: ".o_color_picker_inputs :iframe input",
            run: "edit #00000080 && click body",
        },
        {
            content: "Wait for the operation to finish",
            trigger: ".o_website_preview :iframe:not(:has(.o_loading_screen))",
        },
        {
            content: "Check that the blur option appears for transparent gradients",
            trigger: headerBlurRangeSelector,
        },
    ],
});
