import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { addBuilderOption } from "@html_builder/../tests/helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { getIframeInput } from "@html_editor/../tests/_helpers/iframe_input";
import {
    defineWebsiteModels,
    mockThemeRpcs,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("BuilderColorPicker with action “customizeWebsiteColor” is correctly displayed", async () => {
    mockThemeRpcs();
    addBuilderOption({
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
        // The gray picked below, as the bundle prints it: the mocked preview
        // CSS replaces the bundle's.
        styleContent: ":root { --400: #CED4DA; }",
    });
    await contains(":iframe .test-options-target").click();
    await animationFrame();
    expect(".o_hb_tab_content > .o_customize_tab").toHaveCount(1);

    expect.step("set preset");
    await contains("button.o_we_color_preview").click();
    await contains("button[data-color='o_cc4'").click();
    await expect.waitForSteps([
        "set preset",
        `preview user_values.scss {"test-gradient":"NULL"} user_color_palette.scss {"test-custom":"NULL","test":4}`,
    ]);

    // Setting solid color does not impact preset
    expect.step("set solid color");
    await contains("button.o_we_color_preview").click();
    await contains("button.custom-tab").click();
    await contains("button[data-color='400']").click();
    await expect.waitForSteps([
        "set solid color",
        `preview user_values.scss {"test-gradient":"NULL"} user_color_palette.scss {"test-custom":"#CED4DA","test":4}`,
    ]);

    // Setting preset does not impact solid color
    expect.step("set preset on solid color");
    await contains("button.o_we_color_preview").click();
    await contains("button.theme-tab").click();
    await contains("button[data-color='o_cc3'").click();
    await expect.waitForSteps([
        "set preset on solid color",
        `preview user_values.scss {"test-gradient":"NULL"} user_color_palette.scss {"test-custom":"NULL","test":3}`,
    ]);

    // Setting gradient does not impact preset
    expect.step("set gradient");
    await contains("button.o_we_color_preview").click();
    await contains("button.gradient-tab").click();
    await contains("button.o_gradient_color_button").click();
    await expect.waitForSteps([
        "set gradient",
        `preview user_values.scss {"test-gradient":"linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)"} user_color_palette.scss {"test-custom":"NULL","test":3}`,
    ]);

    // Setting preset does not impact gradient
    expect.step("set preset on gradient");
    await contains("button.o_we_color_preview").click();
    await contains("button.theme-tab").click();
    await contains("button[data-color='o_cc4'").click();
    await expect.waitForSteps([
        "set preset on gradient",
        `preview user_values.scss {"test-gradient":"NULL"} user_color_palette.scss {"test-custom":"NULL","test":4}`,
    ]);

    // Clear clears everything
    expect.step("reset");
    await contains("button.o_we_color_preview").click();
    await contains(".o_font_color_selector [data-icon='delete'].oi-filled").click();
    await expect.waitForSteps([
        "reset",
        `preview user_values.scss {"test-gradient":"NULL"} user_color_palette.scss {"test-custom":"NULL","test":"NULL"}`,
    ]);

    await contains('.o_hb_snippets_tabs button[data-name="theme"]').click();
    await contains(".o_hb_tab_content .o_hb_theme_color_slider_btn").click();
    await contains(
        '.o_hb_sliding_panel_content button[aria-controls^="builder_collapse_content_"]'
    ).click();
    await contains(
        '.o_hb_sliding_panel_content div[data-label="Background"] .o_we_color_preview'
    ).click();
    await contains(".o_hb_colorpicker .custom-tab").click();
    const hexInputEl = await getIframeInput(
        ".o_font_color_selector .o_color_picker_inputs iframe.o_hex_iframe",
        "input[name='hex_input']"
    );
    await contains(hexInputEl).edit("#77FF006E");
    await expect.waitForSteps([
        `preview user_values.scss {"test-gradient":"NULL","o-cc1-bg-gradient":"null"} user_color_palette.scss {"test-custom":"NULL","test":"NULL","o-cc1-bg":"#77FF006E"}`,
    ]);
    const colorPresetEl = document.querySelector("div .o_cc_preview_wrapper div");
    const presetElStyles = window.getComputedStyle(colorPresetEl, "::before");
    expect(presetElStyles.backgroundImage).toInclude("transparent.png");
    expect(presetElStyles.backgroundSize).toInclude("32px");
});
