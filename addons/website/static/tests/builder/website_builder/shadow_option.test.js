import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { addBuilderOption } from "@html_builder/../tests/helpers";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    waitForThemeReveal,
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
    expect.waitForSteps([
        '/website/static/src/scss/options/user_values.scss {"box-shadow-offset-x":"6.25rem"}',
        "asset reload",
    ]);

    await contains("div.hb-row-label:contains('Normal')").click();
    await contains("div[data-label='Color'] button.o_we_color_preview").click();
    await contains("div.o_popover button.o_color_button[data-color='#FF0000']").click();
    expect.waitForSteps([
        '/website/static/src/scss/options/user_values.scss {"box-shadow-color":"#FF0000"}',
        "asset reload",
    ]);
});

test("highlights the shadow size that was edited", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<ShadowOption/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);

    await contains(":iframe .test-options-target").click();
    await contains("[data-label='Shadow'] .o-hb-select-toggle").click();
    await contains(
        ".o_popover .o-hb-select-dropdown-item:contains('Small') a.o-hb-theme-tab-link"
    ).click();

    await waitForThemeReveal();
    expect(".hb-row[data-label='Small']").toHaveClass("o-hb-row-highlight");
    expect(".hb-row.o-hb-row-highlight").toHaveCount(1);
    expect(".hb-row[data-label='Small'] + .hb-collapse-content [data-label='Blur']").toHaveCount(1);
});
