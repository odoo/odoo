import { expect, test } from "@odoo/hoot";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import { queryOne } from "@odoo/hoot-dom";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("change bootstrap border radius values in the theme tab of website builder", async () => {
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(_, changes) {
            const iframeDoc = queryOne(":iframe").documentElement;
            for (const [variable, value] of Object.entries(changes)) {
                iframeDoc.style.setProperty(`--${variable}`, value);
            }
        }
    }
    defineModels([WebsiteAssets]);

    onRpc("/website/theme_customize_bundle_reload", (request) => {
        expect.step("asset reload");
        return "";
    });

    const { waitSidebarUpdated } = await setupWebsiteBuilder("");
    await contains("#theme-tab").click();

    // Change the border-radius variable and check that the dependent variables
    // are updated accordingly.
    await contains("[data-label='Roundness'] input[type='number']").edit(10);
    await expect.waitForSteps(["asset reload"]);

    expect("[data-action-id='customizeBorderRadiusVariable'] input[type='number']").toHaveValue(10);
    await contains("div.hb-row-label:contains('Roundness')").click();
    expect("[data-action-param='border-radius-sm'] input").toHaveValue(8);

    // Change the border-radius-sm variable and check that the reset button is
    // displayed.
    expect("button[data-action-id='resetBorderRadius']").toHaveCount(0);
    await contains("[data-action-param='border-radius-sm'] input").edit(10);
    await expect.waitForSteps(["asset reload"]);
    // await contains("div[data-label='Roundness'] + * div[data-label='Small']").click();
    await waitSidebarUpdated();
    expect("button[data-action-id='resetBorderRadius']").toHaveCount(1);

    // Change the border-radius variable again and check that border-radius-sm
    // is not updated (because it has been customized).
    await contains("[data-action-id='customizeBorderRadiusVariable'] input[type='number']").edit(
        20
    );
    await expect.waitForSteps(["asset reload"]);
    expect("[data-action-param='border-radius-sm'] input").toHaveValue(10);
});
