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

    await contains('.o-snippets-tabs button[data-name="theme"]').click();
    await contains('.o_theme_tab div[data-label="Color Presets"] button').click();
    await contains('div[id^="builder_collapse_content_"] button').click();
    await contains('div[data-label="Background"] .o_we_color_preview').click();
    await contains(".o-hb-colorpicker .custom-tab").click();
    await contains(".o_color_picker_inputs input.o_hex_input").edit("#77FF006E");
    // When writing "#77FF006E" in the input, a first call is made when the
    // input value is "#77FF00" and another when it becomes "#77FF006E"
    await expect.waitForSteps([
        '/website/static/src/scss/options/colors/user_color_palette.scss {"o-cc1-bg":"#77FF00"}',
        '/website/static/src/scss/options/user_values.scss {"o-cc1-bg-gradient":"null"}',
        "asset reload",
        '/website/static/src/scss/options/colors/user_color_palette.scss {"o-cc1-bg":"#77FF006E"}',
        '/website/static/src/scss/options/user_values.scss {"o-cc1-bg-gradient":"null"}',
        "asset reload",
    ]);
    const colorPresetEl = document.querySelector(
        'div[id^="builder_collapse_content_"] .o_cc_preview_wrapper div'
    );
    const presetElStyles = window.getComputedStyle(colorPresetEl, "::before");
    expect(presetElStyles.backgroundImage).toInclude("transparent.png");
    expect(presetElStyles.backgroundSize).toBe("32px");
});
