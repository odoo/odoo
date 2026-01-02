import {
    changeOption,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
    goToTheme,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "shape_color_sync_with_theme_color",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_company_team",
            name: "Team",
            groupName: "People",
        }),
        ...clickOnSnippet(".s_company_team"),
        changeOption("Team", "toggleBgShape"),
        {
            content: "Click on the first shape",
            trigger: "button[data-action-value='web_editor/Connections/01']",
            run: "click",
        },
        {
            content: "Open the color picker",
            trigger: "[data-label='Colors'] .o_we_color_preview",
            run: "click",
        },
        {
            content: "Set the shape color to theme color 1",
            trigger: ".o_colorpicker_section [data-color='o-color-1']",
            run: "click",
        },
        ...goToTheme(),
        {
            content: "Open the color picker for theme preset 1",
            trigger: "[data-container-title='Colors'] .o_we_color_preview",
            run: "click",
        },
        {
            content: "Update the color value",
            trigger: ".o_colorpicker_widget input",
            run: "edit 1AEF74",
        },
        {
            content: "Wait until loading is completed",
            trigger: ":iframe body:not(:has(.o_we_ui_loading))",
        },
        {
            content: "Verify that the shape color is updated",
            trigger: ":iframe .s_company_team",
            run() {
                const backgroundImageUrl =
                    this.anchor.querySelector(".o_we_shape").style.backgroundImage;
                if (!backgroundImageUrl.includes("1AEF74")) {
                    throw new Error(
                        "Updating the theme color should also update the background shape color."
                    );
                }
            },
        },
    ]
);
