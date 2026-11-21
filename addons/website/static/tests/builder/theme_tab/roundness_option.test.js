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
            expect.step(JSON.stringify(changes));
            for (const [variable, value] of Object.entries(changes)) {
                if (value === "NULL") {
                    delete customizedRadii[variable];
                } else {
                    customizedRadii[variable] = value;
                }
            }
            // [grep: border-radius-multipliers] Mimic the SCSS fallbacks: small
            // and large radii follow the normal radius (x0.75 / x1.5) unless
            // explicitly customized.
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

    const { waitSidebarUpdated } = await setupWebsiteBuilder("");
    await contains("#theme-tab").click();
    const numberInput = (label) =>
        `[data-container-title='Roundness'] [data-label='${label}'] input[type='number']`;
    const resetButton = (label) =>
        `[data-container-title='Roundness'] [data-label='${label}'] ` +
        `button[title='Scale with Roundness']`;

    // Change the border-radius variable and check that the dependent variables
    // are updated accordingly.
    await contains(numberInput("Roundness")).edit(7);
    await expect.waitForSteps(['{"border-radius":"0.4375rem"}', "asset reload"]);
    await waitSidebarUpdated();

    expect(numberInput("Roundness")).toHaveValue(7);
    await contains(
        "[data-container-title='Roundness'] .o_hb_row_label:contains('Roundness')"
    ).click();
    expect(numberInput("Small")).toHaveValue(5.25);
    expect(numberInput("Large")).toHaveValue(10.5);

    // Change the border-radius-sm variable and check that the reset button is
    // displayed.
    expect(resetButton("Large")).toHaveCount(0);
    await contains(numberInput("Small")).edit(10);
    await expect.waitForSteps(['{"border-radius-sm":"0.625rem"}', "asset reload"]);
    await waitSidebarUpdated();
    expect(resetButton("Small")).toHaveCount(1);
    expect(resetButton("Large")).toHaveCount(0);

    // Change the border-radius variable again and check that border-radius-sm
    // is not updated (because it has been customized).
    await contains(numberInput("Roundness")).edit(20);
    await expect.waitForSteps(['{"border-radius":"1.25rem"}', "asset reload"]);
    await waitSidebarUpdated();
    expect(numberInput("Small")).toHaveValue(10);
    expect(numberInput("Large")).toHaveValue(30);

    // Reset restores the proportional size after a custom value.
    await contains(resetButton("Small")).click();
    await expect.waitForSteps(['{"border-radius-sm":"NULL"}', "asset reload"]);
    await waitSidebarUpdated();
    expect(numberInput("Small")).toHaveValue(15);
    expect(resetButton("Small")).toHaveCount(0);
});
