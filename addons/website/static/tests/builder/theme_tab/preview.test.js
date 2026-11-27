import { expect, test } from "@odoo/hoot";
import {
    advanceTime,
    animationFrame,
    queryAll,
    queryFirst,
    tick,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    mockThemeRpcs,
    PALETTE_URL,
    saveWebsite,
    setPrimaryColor,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithDummySnippet,
    switchPalette,
    USER_VALUES_URL as USER_VALUES,
    waitForSnippetDialog,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

// The preview of a paragraph margin of 8px (see `mockThemeRpcs`).
const MARGIN_PREVIEW = 'preview user_values.scss {"paragraph-margin-top":"8px"}';

// The preview CSS answers, in order (each a CSS or its promise).
function mockPreviewCSS(...responses) {
    onRpc("/website/theme_preview_css", async () => ({
        css: await responses.shift(),
        font_urls: [],
    }));
}

// The number box of an option.
function numberInput(variable) {
    return `[data-action-param='${variable}'] input.o_hb_input_number`;
}

// As the preview CSS prints it (see `mockThemeRpcs`).
function getPreviewedValue(variable, iframeSelector = "") {
    const htmlEl = queryFirst(`${iframeSelector} :iframe html`.trim());
    return getComputedStyle(htmlEl).getPropertyValue(`--${variable}`).trim();
}

test("theme tab: a value is previewed, undone, redone and written on save", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();

    await contains(numberInput("paragraph-margin-top")).edit("8");
    await expect.waitForSteps([MARGIN_PREVIEW]);
    expect(getPreviewedValue("paragraph-margin-top")).toBe("8px");

    // Nothing pending anymore: the saved CSS is back, nothing to compile.
    await contains(".o_hb_snippets_top_actions button[data-icon='undo']").click();
    expect(getPreviewedValue("paragraph-margin-top")).toBe("");
    expect(":iframe style.o_theme_preview_css").toHaveCount(0);

    await contains(".o_hb_snippets_top_actions button[data-icon='redo']").click();
    await expect.waitForSteps([MARGIN_PREVIEW]);
    expect(getPreviewedValue("paragraph-margin-top")).toBe("8px");

    await saveWebsite();
    expect.verifySteps([`${USER_VALUES} {"paragraph-margin-top":"8px"}`]);
});

test("theme tab: the preview CSS replaces the frontend bundle's", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("", { loadIframeBundles: true });
    await contains("#theme-tab").click();
    const linkSelector = ":iframe link[href*='web.assets_frontend']";
    expect(linkSelector).toHaveCount(1);

    await contains(numberInput("paragraph-margin-top")).edit("8");
    await expect.waitForSteps([MARGIN_PREVIEW]);
    expect(queryFirst(linkSelector).sheet.disabled).toBe(true);
    // In the bundle's place, before the stylesheets that come after it.
    expect(queryFirst(linkSelector).nextElementSibling).toHaveClass("o_theme_preview_css");

    await contains(".o_hb_snippets_top_actions button[data-icon='undo']").click();
    expect(queryFirst(linkSelector).sheet.disabled).toBe(false);
    expect(":iframe style.o_theme_preview_css").toHaveCount(0);
});

test("theme tab: the latest preview CSS wins", async () => {
    const firstCSS = Promise.withResolvers();
    mockPreviewCSS(firstCSS.promise, ":root { --paragraph-margin-top: 12px; }");
    const { getEditor } = await setupWebsiteBuilder("");
    const { customizeWebsiteVariables } = getEditor().shared.customizeWebsite;

    const firstChange = customizeWebsiteVariables({ "paragraph-margin-top": "8px" });
    await customizeWebsiteVariables({ "paragraph-margin-top": "12px" });
    expect(getPreviewedValue("paragraph-margin-top")).toBe("12px");
    // The first CSS comes back last: dropped.
    firstCSS.resolve(":root { --paragraph-margin-top: 8px; }");
    await firstChange;
    expect(getPreviewedValue("paragraph-margin-top")).toBe("12px");
});

test("theme tab: undo shows the loading effect while it compiles", async () => {
    const undoCSS = Promise.withResolvers();
    mockPreviewCSS(":root {}", ":root {}", undoCSS.promise);
    await setupWebsiteBuilder("", { loadIframeBundles: true });
    await contains("#theme-tab").click();
    await contains(numberInput("paragraph-margin-top")).edit("8");
    await contains(numberInput("paragraph-margin-top")).edit("12");

    await contains(".o_hb_snippets_top_actions button[data-icon='undo']").click();
    await advanceTime(500); // the loading effect's delay
    expect(":iframe .o_loading_screen.o_we_ui_loading").toHaveCount(1);
    undoCSS.resolve(":root {}");
    await tick();
    expect(":iframe .o_loading_screen").toHaveCount(0);
});

test("theme tab: the UI is blocked while the preview compiles", async () => {
    const previewCSS = Promise.withResolvers();
    mockPreviewCSS(previewCSS.promise);
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();

    await contains(numberInput("paragraph-margin-top")).edit("8");
    expect(".o_blockUI").toHaveCount(1);
    previewCSS.resolve(":root {}");
    await animationFrame();
    expect(".o_blockUI").toHaveCount(0);
});

test("theme tab: the snippets' previews show the pending values", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilderWithDummySnippet();
    await contains("#theme-tab").click();
    await contains(numberInput("paragraph-margin-top")).edit("8");
    await expect.waitForSteps([MARGIN_PREVIEW]);

    await contains("#blocks-tab").click();
    await contains("[data-snippet-group='a'] .o_snippet_thumbnail_area").click();
    await waitForSnippetDialog();
    expect(getPreviewedValue("paragraph-margin-top", ".o_add_snippet_dialog")).toBe("8px");
});

test("theme tab: the colors preview shows the pending values", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();
    await contains(numberInput("paragraph-margin-top")).edit("8");
    await expect.waitForSteps([MARGIN_PREVIEW]);

    await contains(".o_hb_theme_color_slider_btn").click();
    await contains(".o_theme_tab button[title='Colors preview']").click();
    await waitFor(".o_theme_colors_preview_dialog :iframe style.o_theme_preview_css");
    expect(getPreviewedValue("paragraph-margin-top", ".o_theme_colors_preview_dialog")).toBe("8px");
});

test("theme tab: the pending values stay on top of a bundle reload", async () => {
    mockThemeRpcs();
    const { getEditor } = await setupWebsiteBuilder("", { loadIframeBundles: true });
    const linkSelector = ":iframe link[href*='web.assets_frontend']";
    const bundleURL = queryFirst(linkSelector).getAttribute("href");
    onRpc("/website/theme_customize_bundle_reload", () => ({
        "web.assets_frontend": [bundleURL],
        font_urls: [],
    }));
    await contains("#theme-tab").click();
    await contains(numberInput("paragraph-margin-top")).edit("8");
    await expect.waitForSteps([MARGIN_PREVIEW]);

    // As after a write outside the editor (e.g. by the AI website builder).
    await getEditor().shared.customizeWebsite.reloadBundles();
    expect.verifySteps([MARGIN_PREVIEW]);
    expect(queryAll(linkSelector).map((el) => el.sheet.disabled)).toEqual([true]);
    expect(getPreviewedValue("paragraph-margin-top")).toBe("8px");
});

test("theme tab: the fonts of the pending values are loaded once", async () => {
    const fontURL = "/web/content/1/google-font-Raleway";
    onRpc("/website/theme_preview_css", () => ({ css: ":root {}", font_urls: [fontURL] }));
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();

    await contains(numberInput("paragraph-margin-top")).edit("8");
    expect(`:iframe link[href='${fontURL}']`).toHaveCount(1);
    await contains(numberInput("paragraph-margin-top")).edit("12");
    expect(`:iframe link[href='${fontURL}']`).toHaveCount(1);
});

test("theme tab: the fonts reloaded with the bundles are not loaded again", async () => {
    const fontURL = "/web/content/1/google-font-Raleway";
    onRpc("/website/theme_preview_css", () => ({ css: ":root {}", font_urls: [fontURL] }));
    onRpc("/website/theme_customize_bundle_reload", () => ({ font_urls: [fontURL] }));
    const { getEditor } = await setupWebsiteBuilder("");
    await contains("#theme-tab").click();
    await contains(numberInput("paragraph-margin-top")).edit("8");

    // The reloaded font's link ends with `#t=<time>`.
    await getEditor().shared.customizeWebsite.reloadBundles();
    expect(`:iframe link[href^='${fontURL}']`).toHaveCount(1);
});

// Each kind of value has its own pending values.
const DISCARDED_CHANGES = {
    value: {
        change: () => contains(numberInput("paragraph-margin-top")).edit("8"),
        preview: MARGIN_PREVIEW,
    },
    color: {
        change: async () => {
            await contains(".o_hb_theme_color_slider_btn").click();
            await setPrimaryColor();
        },
        preview: 'preview user_color_palette.scss {"o-color-1":"#FF0000"}',
    },
    palette: {
        change: async () => {
            await contains(".o_hb_theme_color_slider_btn").click();
            await switchPalette();
        },
        preview: `preview user_values.scss {"color-palettes-name":"'default-light-1'"}`,
    },
};
for (const [kind, { change, preview }] of Object.entries(DISCARDED_CHANGES)) {
    test(`theme tab: discard writes no ${kind}`, async () => {
        mockThemeRpcs();
        await setupWebsiteBuilder("");
        await contains("#theme-tab").click();

        await change();
        await expect.waitForSteps([preview]);
        await contains(".o_hb_snippets_top_actions [data-action='cancel']").click();
        await contains(".modal-content button.btn-primary").click();
        await waitForNone(".o_hb_snippets_top_actions");
        expect.verifySteps([]);
    });
}

test("theme tab: a view switch saves the pending values", async () => {
    mockThemeRpcs();
    onRpc("/website/theme_customize_data", () => {
        expect.step("views written");
    });
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();

    await contains(numberInput("paragraph-margin-top")).edit("8");
    await expect.waitForSteps([MARGIN_PREVIEW]);
    // Saved and reloaded, without compiling a preview first.
    await contains("[data-label='Show Header'] input[type='checkbox']").click();
    await expect.waitForSteps(["views written", `${USER_VALUES} {"paragraph-margin-top":"8px"}`]);
});

test("theme tab: a color is written in its file on save, after the values", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();
    await contains(numberInput("paragraph-margin-top")).edit("8");
    await contains(".o_hb_theme_color_slider_btn").click();
    await setPrimaryColor();
    await expect.waitForSteps([
        MARGIN_PREVIEW,
        `${MARGIN_PREVIEW} user_color_palette.scss {"o-color-1":"#FF0000"}`,
    ]);

    await saveWebsite();
    expect.verifySteps([
        `${USER_VALUES} {"paragraph-margin-top":"8px"}`,
        `${PALETTE_URL} {"o-color-1":"#FF0000"}`,
    ]);
});
