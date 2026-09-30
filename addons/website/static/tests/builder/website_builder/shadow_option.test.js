import { expect, test } from "@odoo/hoot";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();
test("bootstrap shadow controls in the theme tab of website builder", async () => {
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            expect.step(`${location} ${JSON.stringify(changes)}`);
        }
    }
    defineModels([WebsiteAssets]);
    onRpc("/website/theme_customize_bundle_reload", async (request) => {
        expect.step("asset reload");
        return "";
    });
    await setupWebsiteBuilder("");

    await contains("#theme-tab").click();
    await contains("[data-action-param='box-shadow-offset-x'] input").fill("100");
    expect(":iframe html").toHaveStyle({ "--box-shadow-offset-x": "6.25rem" }, { inline: true });

    await contains("div.hb-row-label:contains('Normal')").click();
    await contains("div[data-label='Color'] button.o_we_color_preview").click();
    await contains("div.o_popover button.o_color_button[data-color='#FF0000']").click();
    expect(":iframe html").toHaveStyle({ "--box-shadow-color": "#FF0000" }, { inline: true });
    // Previewed only: written on save, without a bundle reload.
    expect.verifySteps([]);

    await contains(".o-snippets-top-actions [data-action='save']").click();
    await expect.waitForSteps([
        '/website/static/src/scss/options/user_values.scss {"box-shadow-offset-x":"6.25rem","box-shadow-color":"#FF0000"}',
    ]);
});
