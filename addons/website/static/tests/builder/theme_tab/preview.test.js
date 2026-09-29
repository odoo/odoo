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

    await contains(".o_theme_tab .hb-row[data-label='Background']:last .o_we_color_preview").click();
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

test("theme tab: a palette switch drops the previewed colors it resets", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("", { loadIframeBundles: true });
    await openThemeTab();
    await contains(".o-tab-content .o-hb-theme-color-slider-btn").click();
    await contains("button.o_we_color_preview[title='Primary']").click();
    await contains(".o_popover button.solid-tab").click();
    await contains(".o_popover button.o_color_button[data-color='#FF0000']").click();
    expect(websiteRootStyle().getPropertyValue("--o-color-1")).toBe("#FF0000");

    await contains(".o_theme_tab [data-icon='palette']").click();
    await contains(`[data-action-value="'default-light-1'"] .o-color-palette-card span`).click();
    // Confirmed, as the previewed color will be lost.
    await contains(".o_dialog .btn-primary").click();
    await expect.waitForSteps([
        `${USER_VALUES} {"color-palettes-name":"'default-light-1'"}`,
        "asset reload",
    ]);
    expect(websiteRootStyle().getPropertyValue("--o-color-1")).toBe("");
    expect(websiteRootStyle().getPropertyValue("--o-preview-colors")).toBe("");

    await save();
    expect.verifySteps([]);
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

    expect(action.getVariablesToUpdate(params, "'Roboto'", [{ value: 400 }, { value: 700 }])).toEqual({
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
    await contains("div[data-container-title='Color Presets'] button.o_hb_collapse_toggler").click();
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
