import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Change dynamic SVG colors", async () => {
    const imgPath = "/html_editor/shape/website/s_attributes_1.svg";
    await setupWebsiteBuilder(`<img src="${imgPath}?c1=%23000000">`, {
        styleContent: `
            :root {
                --o-color-1: #111111;
                --white: #FFFFFF;
            }`,
    });

    const svg = await waitFor(":iframe img");
    await contains(svg).click();

    // The bigger timeout is there to prevent undetermistic behaviors linked to
    // SVG being downloaded from the server when the <img> src attribute is modified.
    const colorPreviewButton = await waitFor(
        '[data-label="Dynamic Colors"] button.o_we_color_preview',
        { timeout: 1000 }
    );
    const expectColors = async (expectedHex, expectedRgb, expectedParam) => {
        await waitFor(
            `[data-label="Dynamic Colors"] button.o_we_color_preview[style="background-color: ${expectedHex}"]`,
            { timeout: 1000 }
        );
        expect(svg).toHaveAttribute("src", `${imgPath}?c1=${expectedParam}`);
        expect(colorPreviewButton).toHaveStyle({ backgroundColor: expectedRgb });
    };
    await expectColors("#000000", "rgb(0, 0, 0)", "%23000000");

    await contains(colorPreviewButton).click();
    await contains(".o_colorpicker_section button[data-color='o-color-1']").click();
    await expectColors("#111111", "rgb(17, 17, 17)", "o-color-1");

    await contains(colorPreviewButton).click();
    await contains(".o_color_section button[data-color='#FF0000']").click();
    await expectColors("#FF0000", "rgb(255, 0, 0)", "%23FF0000");

    await contains(colorPreviewButton).click();
    await contains(".o_font_color_selector .btn-tab:not(.active)").click();
    await contains(".o_colorpicker_section button[data-color='white']").click();
    await expectColors("#FFFFFF", "rgb(255, 255, 255)", "%23FFFFFF");
});
