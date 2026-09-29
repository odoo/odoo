import { expect, queryFirst, test } from "@odoo/hoot";
import { waitForNone } from "@odoo/hoot-dom";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

const USER_VALUES = "/website/static/src/scss/options/user_values.scss";
const USER_COLORS = "/website/static/src/scss/options/colors/user_color_palette.scss";

function mockThemeRpcs() {
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            expect.step(`${location} ${JSON.stringify(changes)}`);
        }
    }
    defineModels([WebsiteAssets]);
    onRpc("/website/theme_customize_bundle_reload", () => {
        expect.step("asset reload");
        return "";
    });
}

async function openThemeTab() {
    await contains(".o-snippets-tabs button[data-name=theme]").click();
}

function rowInput(variable) {
    return `.hb-row:has([data-action-param='${variable}']) input.o-hb-input-number`;
}

function websiteRootStyle() {
    return queryFirst(":iframe html").style;
}

async function save() {
    await contains(".o-snippets-top-actions [data-action='save']").click();
    await waitForNone(".o-snippets-top-actions");
}

test("theme tab: a number value is previewed, undone, redone and written on save", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");
    await openThemeTab();

    await contains(rowInput("paragraph-margin-top")).edit("8");
    expect(websiteRootStyle().getPropertyValue("--paragraph-margin-top")).toBe("8px");
    expect(websiteRootStyle().getPropertyValue("--o-preview-paragraph-margin-top")).toBe("8px");

    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    expect(websiteRootStyle().getPropertyValue("--paragraph-margin-top")).toBe("");
    expect(websiteRootStyle().getPropertyValue("--o-preview-paragraph-margin-top")).toBe("");

    await contains(".o-snippets-top-actions button[data-icon='redo']").click();
    expect(websiteRootStyle().getPropertyValue("--paragraph-margin-top")).toBe("8px");
    expect.verifySteps([]);

    await save();
    expect.verifySteps([`${USER_VALUES} {"paragraph-margin-top":"8px"}`]);
});

test("theme tab: discard writes no previewed value", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");
    await openThemeTab();

    await contains(rowInput("paragraph-margin-top")).edit("8");
    await contains(".o-snippets-top-actions button[data-action='cancel']").click();
    await contains(".modal-content button.btn-primary").click();
    await waitForNone(".o-snippets-top-actions");
    expect.verifySteps([]);
});

test("theme tab: the reset button previews the default and resets on save", async () => {
    mockThemeRpcs();
    // The defaults are printed by the compiled CSS.
    await setupWebsiteBuilder("", { loadIframeBundles: true });
    await openThemeTab();

    await contains(rowInput("body-line-height")).edit("2");
    expect(websiteRootStyle().getPropertyValue("--body-line-height")).toBe("2");
    await contains(
        ".hb-row:has([data-action-param='body-line-height']) button[title='Reset to default']"
    ).click();
    expect(websiteRootStyle().getPropertyValue("--body-line-height")).toBe("1.5");
    expect(websiteRootStyle().getPropertyValue("--o-preview-body-line-height")).toBe("1.5");
    expect(rowInput("body-line-height")).toHaveValue(1.5);

    await save();
    expect.verifySteps([`${USER_VALUES} {"body-line-height":"null"}`]);
});

test("theme tab: a color is previewed, undone, redone and written on save", async () => {
    mockThemeRpcs();
    // The color preview is computed from the compiled colors.
    await setupWebsiteBuilder("", { loadIframeBundles: true });
    await openThemeTab();

    await contains(
        ".o_theme_tab .hb-row[data-label='Background']:last .o_we_color_preview"
    ).click();
    await contains(".o_popover button.o_color_button[data-color='#FF0000']").click();
    expect(websiteRootStyle().getPropertyValue("--input")).toBe("#FF0000");
    expect(websiteRootStyle().getPropertyValue("--o-preview-colors")).toBe("1");

    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    expect(websiteRootStyle().getPropertyValue("--input")).toBe("");
    expect(websiteRootStyle().getPropertyValue("--o-preview-colors")).toBe("");

    await contains(".o-snippets-top-actions button[data-icon='redo']").click();
    expect(websiteRootStyle().getPropertyValue("--input")).toBe("#FF0000");
    expect.verifySteps([]);

    await save();
    expect.verifySteps([`${USER_COLORS} {"input":"#FF0000"}`]);
});

test("theme tab: a font change keeps the weights the new font has, else the nearest", async () => {
    const { getEditor } = await setupWebsiteBuilder("");
    const editor = getEditor();
    editor.shared.customizeWebsite.previewWebsiteVariables({
        "lead-font-weight": "300",
        "font-weight-normal": "500",
        "font-weight-bolder": "700",
    });
    const action = editor.shared.builderActions.getAction("previewWebsiteFontFamily");
    const params = { mainParam: "font" };

    expect(
        action.getVariablesToUpdate(params, "'Roboto'", [{ value: 400 }, { value: 700 }])
    ).toEqual({
        font: "'Roboto'",
        "lead-font-weight": "400",
        "font-weight-normal": "400",
    });
    // Unknown weights: reset.
    expect(action.getVariablesToUpdate(params, "'Roboto'", [])).toEqual({
        font: "'Roboto'",
        "font-weight-normal": "null",
        "lead-font-weight": "null",
        "font-weight-bolder": "null",
    });
    // "Auto" stays.
    editor.shared.customizeWebsite.previewWebsiteVariables({ "font-weight-bolder": "" });
    expect(action.getVariablesToUpdate(params, "'Roboto'", [{ value: 400 }])).toEqual({
        font: "'Roboto'",
        "lead-font-weight": "400",
        "font-weight-normal": "400",
        "font-weight-bolder": "null",
    });
});

test("theme tab: the page background follows the colors in every layout", async () => {
    await setupWebsiteBuilder("", { loadIframeBundles: true });
    await openThemeTab();
    await contains(".o-tab-content .o-hb-theme-color-slider-btn").click();
    await contains(
        "div[data-container-title='Color Presets'] button.o_hb_collapse_toggler"
    ).click();
    await contains(
        "div[id^='builder_collapse_content'] div[data-label='Background'] .o_we_color_preview"
    ).click();
    await contains(".o_popover button.solid-tab").click();
    await contains(".o_popover button.o_color_button[data-color='#0000FF']").click();

    // The full layout's page background is the first preset's.
    expect(queryFirst(":iframe body")).toHaveStyle({ backgroundColor: "rgb(0, 0, 255)" });
    // The other layouts' is the "body" color, which Sass prints by name.
    expect(websiteRootStyle().getPropertyValue("--o-preview-boxed-body-fill")).toBe(
        "rgb(255, 255, 255)"
    );
});

test("theme tab: the link style is previewed and written on save", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder(`<p><a href="#">link</a></p>`, { loadIframeBundles: true });
    await openThemeTab();

    await contains("[data-label='Link Style'] .o-hb-select-toggle").click();
    await contains(".o-hb-select-dropdown-item:contains('Always Underline')").click();
    expect(":iframe a[href='#']").toHaveStyle({ textDecorationLine: "underline" });
    expect.verifySteps([]);

    await save();
    expect.verifySteps([`${USER_VALUES} {"link-underline":"always"}`]);
});

test("theme tab: the button style is previewed and written on save", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder(
        `<a href="#" class="btn btn-primary">button</a>
        <section class="o_cc o_cc2"><a href="#" class="btn btn-primary">button</a></section>`,
        { loadIframeBundles: true }
    );
    await openThemeTab();
    const buttonStyle = () => getComputedStyle(queryFirst(":iframe #wrap > .btn-primary"));
    const presetButtonStyle = () => getComputedStyle(queryFirst(":iframe .o_cc2 .btn-primary"));
    const fillBackground = buttonStyle().backgroundColor;

    await contains("[data-label='Primary Style'] .o-hb-select-toggle").click();
    await contains(".o-hb-select-dropdown-item:contains('Outline')").click();
    expect(buttonStyle().backgroundColor).toBe("rgba(0, 0, 0, 0)");
    expect(buttonStyle().borderColor).toBe(
        websiteRootStyle().getPropertyValue("--o-preview-theme-btn-primary-outline")
    );
    // In a preset, with the preset's colors.
    expect(presetButtonStyle().backgroundColor).toBe("rgba(0, 0, 0, 0)");
    expect(presetButtonStyle().borderColor).toBe(
        websiteRootStyle().getPropertyValue("--o-preview-o-cc2-btn-primary-outline")
    );

    await contains("[data-label='Primary Style'] .o-hb-select-toggle").click();
    await contains(".o-hb-select-dropdown-item:contains('Flat')").click();
    expect(buttonStyle().backgroundColor).toBe(fillBackground);
    expect(buttonStyle().textTransform).toBe("uppercase");
    expect.verifySteps([]);

    await save();
    expect.verifySteps([
        `${USER_VALUES} {"btn-primary-outline":"false","btn-primary-flat":"true"}`,
    ]);
});

test("theme tab: the click effect is applied on save", async () => {
    mockThemeRpcs();
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step(`assets ${JSON.stringify(params)}`);
    });
    await setupWebsiteBuilder("");
    await openThemeTab();

    await contains("[data-label='On Click Effect'] .o-hb-select-toggle").click();
    await contains(".o-hb-select-dropdown-item:contains('Ripple')").click();
    expect.verifySteps([]);

    await save();
    expect.verifySteps([
        'assets {"is_view_data":false,"enable":["website.ripple_effect_scss","website.ripple_effect_js"],"disable":[],"reset_view_arch":false}',
        `${USER_VALUES} {"btn-ripple":"true"}`,
    ]);
});

test("theme tab: the sliders mark the theme default", async () => {
    // The defaults are printed by the compiled CSS.
    await setupWebsiteBuilder("", { loadIframeBundles: true });
    await openThemeTab();

    const mark = ".hb-row:has([data-action-param='body-line-height']) .o-hb-range-default";
    // 1.5 on the paragraph line height's 1-2.5 range.
    const position = "--o-hb-range-default-position: 0.3333333333333333;";
    expect(mark).toHaveAttribute("style", position);
    // Moving the value does not move the mark.
    await contains(rowInput("body-line-height")).edit("2");
    expect(mark).toHaveAttribute("style", position);
});
