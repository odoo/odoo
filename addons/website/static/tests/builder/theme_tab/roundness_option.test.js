import { expect, test } from "@odoo/hoot";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import { queryOne } from "@odoo/hoot-dom";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("change bootstrap border radius values in the theme tab of website builder", async () => {
    const customizedRadii = {};
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(_, changes) {
            for (const [variable, value] of Object.entries(changes)) {
                if (value === "null" || value === "NULL") {
                    delete customizedRadii[variable];
                } else {
                    customizedRadii[variable] = value;
                }
            }
            // Mimic the SCSS fallbacks: small and large radii follow the normal
            // radius (x0.75 / x1.5) unless explicitly customized.
            const iframeStyle = queryOne(":iframe").documentElement.style;
            const borderRadius = customizedRadii["border-radius"] ?? "0.4rem";
            iframeStyle.setProperty("--border-radius", borderRadius);
            for (const [variable, multiplier] of [
                ["border-radius-sm", 0.75],
                ["border-radius-lg", 1.5],
            ]) {
                iframeStyle.setProperty(
                    `--${variable}`,
                    customizedRadii[variable] ?? `${parseFloat(borderRadius) * multiplier}rem`
                );
            }
        }
    }
    defineModels([WebsiteAssets]);

    onRpc("/website/theme_customize_bundle_reload", () => {
        expect.step("asset reload");
        return "";
    });

    const { waitSidebarUpdated } = await setupWebsiteBuilder("", {
        loadIframeBundles: true,
    });
    await contains("#theme-tab").click();
    const roundnessSelector = "[data-container-title='Roundness']";

    // Change the border-radius variable and check that the dependent variables
    // are updated accordingly.
    await contains(`${roundnessSelector} [data-label='Roundness'] input[type='number']`).edit(7);
    await expect.waitForSteps(["asset reload"]);
    await waitSidebarUpdated();

    expect("[data-action-param='border-radius'] input[type='number']").toHaveValue(7);
    await contains(`${roundnessSelector} div.o_hb_row_label:contains('Roundness')`).click();
    expect(`${roundnessSelector} [data-label='Small'] input[type='number']`).toHaveValue(5.25);
    expect(`${roundnessSelector} [data-label='Large'] input[type='number']`).toHaveValue(10.5);

    // Change the border-radius-sm variable and check that the reset button is
    // displayed.
    expect(
        `${roundnessSelector} [data-label='Roundness'] + div [data-label='Large'] button[title='Reset']`
    ).toHaveCount(0);
    await contains(`${roundnessSelector} [data-label='Small'] input[type='number']`).edit(10);
    await expect.waitForSteps(["asset reload"]);
    await waitSidebarUpdated();
    expect(
        `${roundnessSelector} [data-label='Roundness'] + div [data-label='Small'] button[title='Reset']`
    ).toHaveCount(1);
    expect(
        `${roundnessSelector} [data-label='Roundness'] + div [data-label='Large'] button[title='Reset']`
    ).toHaveCount(0);

    // Change the border-radius variable again and check that border-radius-sm
    // is not updated (because it has been customized).
    await contains("[data-action-param='border-radius'] input[type='number']").edit(20);
    await expect.waitForSteps(["asset reload"]);
    await waitSidebarUpdated();
    expect(`${roundnessSelector} [data-label='Small'] input[type='number']`).toHaveValue(10);
    expect(`${roundnessSelector} [data-label='Large'] input[type='number']`).toHaveValue(30);

    // Reset restores the proportional size after a custom value.
    await contains(
        `${roundnessSelector} [data-label='Roundness'] + div [data-label='Small'] button[title='Reset']`
    ).click();
    await expect.waitForSteps(["asset reload"]);
    await waitSidebarUpdated();
    expect(`${roundnessSelector} [data-label='Small'] input[type='number']`).toHaveValue(15);
    expect(
        `${roundnessSelector} [data-label='Roundness'] + div [data-label='Small'] button[title='Reset']`
    ).toHaveCount(0);
});
