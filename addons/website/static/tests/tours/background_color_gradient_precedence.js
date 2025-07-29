import {
    changeBackgroundColor,
    clickOnSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "background_color_gradient_precedence",
    {
        url: "/",
        edition: true,
    },
    () => [
        {
            content: "Verify that the correct gradient has been applied",
            trigger: ":iframe .o_header_standard nav",
            run() {
                const bg = getComputedStyle(this.anchor)["background-image"];
                if (!bg.includes("linear-gradient(rgb(2, 2, 2), rgb(3, 3, 3))")) {
                    throw new Error("Gradient was NOT applied!");
                }
            },
        },
        ...clickOnSnippet({ id: "o_header_standard", name: "Header" }),
        changeBackgroundColor(),
        {
            content: "Switch to custom colors pane",
            trigger: ".o-hb-colorpicker .custom-tab",
            run: "click",
        },
        {
            content: "Select custom color background",
            trigger: ".o_color_picker_button[data-color='black']",
            run: "click",
        },
        {
            content: "Verify custom color is selected in picker",
            trigger: ".o_we_color_preview[style='background-color: #000000']",
        },
        {
            content: "Verify custom color is applied to Header",
            trigger: ":iframe .o_header_standard nav",
            run() {
                if (
                    getComputedStyle(this.anchor)["background-image"] ===
                    "linear-gradient(rgb(0, 0, 0), rgb(1, 1, 1))"
                ) {
                    throw new Error("Custom color was NOT applied!");
                }
            },
        },
    ]
);
