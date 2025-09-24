import { expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import {
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("BuilderColorPicker with action “customizeWebsiteColor” is correctly displayed", async () => {
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            expect.step(`${location} ${JSON.stringify(changes)}`);
        }
    }
    defineModels([WebsiteAssets]);

    let def = new Deferred();
    onRpc("/website/theme_customize_bundle_reload", async (request) => {
        expect.step("asset reload");
        def.resolve();
        return "";
    });
    addOption({
        selector: ".test-options-target",
        template: xml`
        <BuilderColorPicker
            enabledTabs="['theme', 'custom', 'gradient']"
            preview="false"
            defaultColor="''"
            action="'customizeWebsiteColor'"
            actionParam="{
                mainParam: 'test-custom',
                gradientColor: 'test-gradient',
                combinationColor: 'test',
                nullValue: 'NULL',
            }"
        />
        `,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`, {
        loadIframeBundles: true,
    });
    await contains(":iframe .test-options-target").click();
    await animationFrame();
    expect(".o-tab-content > .o_customize_tab").toHaveCount(1);

    expect.step("set preset");
    await contains("button.o_we_color_preview").click();
    await contains("button[data-color='o_cc4'").click();
    // Should wait for 2 ticks (debounced): customizeWebsiteColors, reloadBundles
    await def;
    expect.verifySteps([
        "set preset",
        '/website/static/src/scss/options/colors/user_color_palette.scss {"test-custom":"NULL","test":4}',
        '/website/static/src/scss/options/user_values.scss {"test-gradient":"NULL"}',
        "asset reload",
    ]);

    def = new Deferred();
    // Setting solid color does not impact preset
    expect.step("set solid color");
    await contains("button.o_we_color_preview").click();
    await contains("button.custom-tab").click();
    await contains("button[data-color='400']").click();
    // Should wait for 2 ticks (debounced): customizeWebsiteColors, reloadBundles
    await def;
    expect.verifySteps([
        "set solid color",
        '/website/static/src/scss/options/colors/user_color_palette.scss {"test-custom":"#CED4DA"}',
        '/website/static/src/scss/options/user_values.scss {"test-gradient":"NULL"}',
        "asset reload",
    ]);

    def = new Deferred();
    // Setting preset does not impact solid color
    expect.step("set preset on solid color");
    await contains("button.o_we_color_preview").click();
    await contains("button.theme-tab").click();
    await contains("button[data-color='o_cc3'").click();
    // Should wait for 2 ticks (debounced): customizeWebsiteColors, reloadBundles
    await def;
    expect.verifySteps([
        "set preset on solid color",
        '/website/static/src/scss/options/colors/user_color_palette.scss {"test-custom":"NULL","test":3}',
        '/website/static/src/scss/options/user_values.scss {"test-gradient":"NULL"}',
        "asset reload",
    ]);

    def = new Deferred();
    // Setting gradient does not impact preset
    expect.step("set gradient");
    await contains("button.o_we_color_preview").click();
    await contains("button.gradient-tab").click();
    await contains("button.o_gradient_color_button").click();
    // Should wait for 3 ticks (debounced): customizeWebsiteColors, customizeWebsiteVariables, reloadBundles
    await def;
    expect.verifySteps([
        "set gradient",
        '/website/static/src/scss/options/colors/user_color_palette.scss {"test-custom":"NULL"}',
        '/website/static/src/scss/options/user_values.scss {"test-gradient":"linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)"}',
        "asset reload",
    ]);

    def = new Deferred();
    // Setting preset does not impact gradient
    expect.step("set preset on gradient");
    await contains("button.o_we_color_preview").click();
    await contains("button.theme-tab").click();
    await contains("button[data-color='o_cc4'").click();
    // Should wait for 2 ticks (debounced): customizeWebsiteColors, reloadBundles
    await def;
    expect.verifySteps([
        "set preset on gradient",
        '/website/static/src/scss/options/colors/user_color_palette.scss {"test-custom":"NULL","test":4}',
        '/website/static/src/scss/options/user_values.scss {"test-gradient":"NULL"}',
        "asset reload",
    ]);

    def = new Deferred();
    // Clear clears everything
    expect.step("reset");
    await contains("button.o_we_color_preview").click();
    await contains(".o_font_color_selector .fa-trash").click();
    // Should wait for 3 ticks (debounced): customizeWebsiteColors, customizeWebsiteVariables, reloadBundles
    await def;
    expect.verifySteps([
        "reset",
        '/website/static/src/scss/options/colors/user_color_palette.scss {"test-custom":"NULL","test":"NULL"}',
        '/website/static/src/scss/options/user_values.scss {"test-gradient":"NULL"}',
        "asset reload",
    ]);
});
