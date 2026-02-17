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
        {
            content: "Click on any image in the snippet",
            trigger: ":iframe .s_company_team img",
            run: "click",
        },
        {
            content: "Open the shape selection dropdown under the image options tab",
            trigger: "[data-label='Shape'] .hb-row-content .dropdown",
            run: "click",
        },
        {
            content: "Click on devices tab",
            trigger: "[data-group-id='devices']",
            run: "click",
        },
        {
            content: "Choose the 'iPhone Front Portrait' shape",
            trigger: "[data-action-value='html_builder/devices/iphone_front_portrait']",
            run: "click",
        },
        {
            content: "Open the color picker",
            trigger: "[data-container-title='Image'] [data-label='Colors'] .o_we_color_preview",
            run: "click",
        },
        {
            content: "Set the shape color to theme color 1",
            trigger: ".o_colorpicker_section [data-color='o-color-1']",
            run: "click",
        },
        {
            content: "Store the shape svg URL in a variable",
            trigger: ":iframe .s_company_team img[data-shape]",
            run() {
                this.initialShapeURL = this.anchor.src;
            },
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
                const updatedShapeURL = this.anchor.querySelector("img[data-shape]").src;
                if (this.initialShapeURL === updatedShapeURL) {
                    throw new Error(
                        "Updating the theme color should also update the image shape color."
                    );
                }
            },
        },
        {
            content: "Click on any image in the snippet",
            trigger: ":iframe .s_company_team img",
            run: "click",
        },
        {
            content: "Check that the color picker icon has changed",
            trigger: "[data-container-title='Image'] [data-label='Colors'] .o_we_color_preview",
            run() {
                // The RGB value of the color #1AEF74 is rgb(26, 239, 116)
                if (this.anchor.style.backgroundColor !== "rgb(26, 239, 116)") {
                    throw new Error(
                        "Updating the theme color should also update the color shown in the color picker"
                    );
                }
            },
        },
    ]
);
