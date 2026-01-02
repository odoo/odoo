import {
    changeBackgroundShape,
    clickOnElement,
    clickOnSnippet,
    goBackToBlocks,
    goToTheme,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const TEST_COLOR_HEX = "1AEF74";

function verifyShapeColorsUpdated(trigger) {
    return {
        content: "Verify that the shape colors are updated",
        trigger,
        run() {
            const backgroundImageUrl =
                this.anchor.querySelector(".o_we_shape").style.backgroundImage;
            if (!backgroundImageUrl.includes(TEST_COLOR_HEX)) {
                throw new Error(
                    "Updating the theme color should also update the background shape color."
                );
            }
        },
    };
}

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
        ...changeBackgroundShape("html_builder/Rainy/01_001"),
        // Ensure shape is transformed so it generates a dynamic SVG URL. It is
        // required because the bug only occurs when the shape is URL-based.
        clickOnElement("flip shape horizontal option", "[data-action-id='flipShape'] .oi-arrows-h"),
        clickOnElement(
            "custom snippet save button",
            "[data-container-title='Team'] .oe_snippet_save"
        ),
        ...goToTheme(),
        clickOnElement(
            "color picker of theme preset 1",
            "[data-container-title='Colors'] .o_we_color_preview"
        ),
        {
            content: "Set theme color to #" + TEST_COLOR_HEX,
            trigger: ".o_colorpicker_widget input",
            run: "edit " + TEST_COLOR_HEX,
        },
        {
            content: "Wait for no loading",
            trigger: "body:not(:has(.o_we_ui_loading)) :iframe body:not(:has(.o_we_ui_loading))",
        },
        verifyShapeColorsUpdated(":iframe .s_company_team"),
        goBackToBlocks(),
        clickOnElement(
            "custom category block",
            ".o_snippet[name='Custom'] .o_snippet_thumbnail_area"
        ),
        verifyShapeColorsUpdated(":iframe .o_snippets_preview_row .s_company_team"),
    ]
);
