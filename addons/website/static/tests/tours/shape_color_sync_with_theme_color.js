import {
    assertCssVariable,
    assertSvgColors,
    changeOption,
    clickOnElement,
    clickOnSnippet,
    goBackToBlocks,
    goToTheme,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const TEST_COLOR_HEX = "1AEF74";
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
        clickOnElement("rainy shape", "[data-action-value='web_editor/Rainy/01_001']"),
        // Ensure shape is transformed so it generates a dynamic SVG URL. It is
        // required because the bug only occurs when the shape is URL-based.
        clickOnElement("flip shape horizontal option", "[data-action-id='flipShape'] .oi-arrows-h"),
        clickOnElement("any image in the snippet", ":iframe .s_company_team img"),
        changeOption("Image", "[data-label='Shape'] .dropdown-toggle"),
        clickOnElement("solid square 3 shape", "[data-action-value$='/solid_square_3']"),
        clickOnElement(
            "custom snippet save button",
            "[data-container-title='Team'] .oe_snippet_save"
        ),
        clickOnElement("save confirmation button", ".modal-dialog button:contains('Save')"),
        ...goToTheme(),
        clickOnElement(
            "Click color palette",
            "div[data-container-title='Colors'] .o-hb-select-wrapper svg"
        ),
        clickOnElement(
            "Change color palette",
            `.o-color-palette-dropdown [data-action-value="'default-light-1'"]`
        ),
        {
            content: "Wait for no loading",
            trigger: "body:not(:has(.o_we_ui_loading))",
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
        {
            content: "Press ESC to close the 'Insert snippet' dialog",
            trigger: ":iframe",
            run: "press Escape",
        },
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
            trigger: "body:not(:has(.o_we_ui_loading))",
        },
        verifyShapeColorsUpdated(":iframe .s_company_team", TEST_COLOR_HEX),
        clickOnElement("any image in the snippet", ":iframe .s_company_team img[data-shape]"),
        assertCssVariable(
            "background-color",
            "rgb(26, 239, 116)",
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
