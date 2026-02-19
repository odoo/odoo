import { stepUtils } from "@web_tour/tour_utils";
import { clickOnSave, goToTheme, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "hide_sidebar_header",
    {
        undeterministicTour_doNotCopy: true, // Remove this key to make the tour failed. ( It removes delay between steps )
        edition: true,
    },
    () => [
        {
            content: "Click on the header",
            trigger: ":iframe #o_main_nav",
            run: "click",
        },
        {
            content: "Click on header template",
            trigger: ".hb-row[data-label='Template'] button.o-hb-select-toggle",
            run: "click",
        },
        {
            content: "Change header template to 'Sidebar'",
            trigger: ".dropdown-menu .o-hb-select-dropdown-item[title='Sidebar']",
            run: "click",
        },
        {
            content: "Wait for the builder to mount after iframe reload",
            trigger: ":iframe body.editor_enable",
        },
        {
            content: "Check that the header changed to 'Sidebar'",
            trigger: ":iframe #wrapwrap>header.o_header_sidebar",
        },
        {
            content: "Check that the builder is not disabled",
            trigger: ".o-website-builder_sidebar:not(:has(.o_builder_disabled))",
        },
        ...goToTheme(),
        {
            content: "Toggle 'Show Header' off",
            trigger: ".hb-row[data-label='Show Header'] input[type='checkbox']",
            run: "click",
        },
        stepUtils.waitIframeIsReady(),
        {
            content: "Check that the header has been hidden",
            trigger: ":iframe #wrapwrap:not(:has(:scope > header))",
        },
        {
            content: "Check that there's no header padding on the #wrapwrap",
            trigger: ":iframe #wrapwrap",
            run() {
                const style = getComputedStyle(this.anchor);
                if (style.paddingLeft !== "0px") {
                    throw new Error("There shouldn't be padding for the header");
                }
            },
        },
        ...clickOnSave(),
    ]
);
