import { registry } from "@web/core/registry";
import {
    changeOptionInPopover,
    clickOnEditAndWaitEditMode,
    clickOnSave,
    selectHeader,
    waitForEditMode,
} from "@website/js/tours/tour_utils";

const headerBlurRangeSelector =
    "[data-container-title='Header'] [data-label='Blur'] input[type='range']";
const headerTemplateBackgroundColorPickerSelector =
    "[data-container-title='Header'] [data-label='Background'] .o_we_color_preview";

function setHeaderBackgroundHex(hexColor) {
    return [
        selectHeader(),
        {
            content: "Open the header background color picker",
            trigger: headerTemplateBackgroundColorPickerSelector,
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
                    const blurValue = getComputedStyle(this.anchor, "::before").getPropertyValue(
                        "--o-bg-blur"
                    );
                    return parseFloat(blurValue) === expectedValue;
                },
                {
                    message: `Expected --o-bg-blur to be ${expectedValue}.`,
                }
            );
        },
    };
}

function checkHeaderBackdropFilter({ content, trigger, pseudoElement }) {
    return {
        content,
        trigger,
        async run({ waitUntil }) {
            await waitUntil(
                () => {
                    const elementStyle = pseudoElement
                        ? getComputedStyle(this.anchor, pseudoElement)
                        : getComputedStyle(this.anchor);
                    const backdropFilter = elementStyle.getPropertyValue("backdrop-filter");
                    return backdropFilter && backdropFilter !== "none";
                },
                {
                    message: `Backdrop filter should've been applied.`,
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
            trigger: `body:not(:has(${headerBlurRangeSelector}))`,
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
            trigger: `body:not(:has(${headerBlurRangeSelector}))`,
        },
        {
            content: "Click on the 'undo' button.",
            trigger: ".o-snippets-top-actions button[data-icon='undo']",
            run: "click",
        },
        // Check that the blue value restored to the previous one.
        checkHeaderBlurValue(5),
        selectHeader(),
        {
            content: "Open the header background color picker",
            trigger: headerTemplateBackgroundColorPickerSelector,
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
        {
            content: "Activate mobile preview",
            trigger: ".o-snippets-top-actions button[data-action='mobile']",
            run: "click",
        },
        {
            content: "Check that the mobile preview is active",
            trigger: ".o-snippets-top-actions button[data-action='mobile'].active",
        },
        checkHeaderBackdropFilter({
            content: `Check that the blur is present in the mobile preview`,
            trigger: ":iframe #wrapwrap > header nav.o_header_mobile",
            pseudoElement: "::before",
        }),
        {
            content: "Open the sidebar",
            trigger: ":iframe header button[data-bs-target='#top_menu_collapse_mobile']",
            run: "click",
        },
        checkHeaderBackdropFilter({
            content: `Check that the blur is present on the sidebar`,
            trigger: ":iframe #wrapwrap > header.o_top_menu_collapse_shown .o_navbar_mobile",
        }),
    ],
});

registry.category("web_tour.tours").add("header_over_the_content_bg_blur_option", {
    steps: () => [
        waitForEditMode,
        selectHeader(),
        ...changeOptionInPopover("Header", "Header Position", "Over the content"),
        {
            content: "Wait for the operation to finish",
            trigger: ".o_website_preview :iframe:not(:has(.o_loading_screen))",
        },
        {
            content: "Check that the header is over the content",
            trigger: ":iframe #wrapwrap.o_header_overlay",
        },
        ...setHeaderBackgroundHex("#000000"),
        {
            content: "Check that the blur option is hidden for an opaque background",
            trigger: `body:not(:has(${headerBlurRangeSelector}))`,
        },
        ...setHeaderBackgroundHex("#00000080"),
        {
            content: "Check that the blur option appears for a transparent background",
            trigger: headerBlurRangeSelector,
        },
    ],
});
