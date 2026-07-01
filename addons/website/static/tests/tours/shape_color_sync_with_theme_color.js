import {
    assertCssVariable,
    assertSvgColors,
    changeBackgroundShape,
    changeImageShape,
    clickOnElement,
    clickOnSnippet,
    goBackToBlocks,
    goToTheme,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const TEST_COLOR_HEX = "00FF00";
const TEST_COLOR_HEX_2 = "7ED1ED";

function verifyShapeColorsUpdated(trigger, expectedHex) {
    return {
        content: "Verify that the shape colors are updated",
        trigger,
        async run() {
            const backgroundImageUrl =
                this.anchor.querySelector(".o_we_shape").style.backgroundImage;
            if (!backgroundImageUrl.includes(expectedHex)) {
                throw new Error(
                    "Updating the theme color should also update the background shape color."
                );
            }
            await assertSvgColors(
                this.anchor.querySelector("img[data-shape]"),
                "Updating the theme color should update the image shape SVG color.",
                [`#${expectedHex}`]
            );
        },
    };
}

registerWebsitePreviewTour(
    "shape_color_sync_with_theme_color",
    {
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
        clickOnElement("any image in the snippet", ":iframe .s_company_team img"),
        ...changeImageShape("html_builder/solid/solid_square_3"),
        clickOnElement(
            "custom snippet save button",
            "[data-container-title='Team'] .oe_snippet_save"
        ),
        ...goToTheme(),
        clickOnElement("color option", "[data-label='Colors'] button"),
        clickOnElement("Click color palette", ".o_theme_tab .hb-sliding-panel .o-dropdown-caret"),
        clickOnElement(
            "Change color palette",
            `.o-color-palette-dropdown [data-action-value="'default-light-1'"]`
        ),
        {
            content: "Wait for no loading",
            trigger: ":iframe body:not(:has(.o_loading_screen))",
        },
        verifyShapeColorsUpdated(":iframe .s_company_team", TEST_COLOR_HEX_2),
        goBackToBlocks(),
        clickOnElement(
            "custom category block",
            ".o_snippet[name='Custom'] .o_snippet_thumbnail_area"
        ),
        verifyShapeColorsUpdated(
            ":iframe .o_snippets_preview_row .s_company_team",
            TEST_COLOR_HEX_2
        ),
        clickOnElement("X to close the 'Insert snippet' dialog", ".modal .btn-close"),
        ...goToTheme(),
        clickOnElement("color option", "[data-label='Colors'] button"),
        clickOnElement(
            "color picker of theme preset 1",
            ".hb-sliding-panel-content .o_we_color_preview"
        ),
        clickOnElement("solid colors tab", ".o_font_color_selector .btn-tab.solid-tab"),
        clickOnElement(
            `#${TEST_COLOR_HEX} color`,
            `.o_font_color_selector .o_color_button[data-color="#${TEST_COLOR_HEX}"]`
        ),
        {
            content: "Wait for no loading",
            trigger: ":iframe body:not(:has(.o_loading_screen))",
        },
        verifyShapeColorsUpdated(":iframe .s_company_team", TEST_COLOR_HEX),
        clickOnElement("any image in the snippet", ":iframe .s_company_team img[data-shape]"),
        assertCssVariable(
            "background-color",
            "rgb(0, 255, 0)",
            "[data-container-title='Image'] [data-label='Colors'] .o_we_color_preview"
        ),
        goBackToBlocks(),
        clickOnElement(
            "custom category block",
            ".o_snippet[name='Custom'] .o_snippet_thumbnail_area"
        ),
        verifyShapeColorsUpdated(":iframe .o_snippets_preview_row .s_company_team", TEST_COLOR_HEX),
    ]
);
