import { expect, test } from "@odoo/hoot";
import { advanceTime, queryFirst, tick, waitForNone } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    mockThemeRpcs,
    PALETTE_URL,
    saveWebsite,
    setupWebsiteBuilder,
    USER_VALUES_URL as USER_VALUES,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

// The number box of an option.
function numberInput(variable) {
    return `[data-action-param='${variable}'] input.o_hb_input_number`;
}

// As the preview CSS prints it (see `mockThemeRpcs`).
function getPreviewedValue(variable) {
    return getComputedStyle(queryFirst(":iframe html")).getPropertyValue(`--${variable}`).trim();
}

test("theme tab: a value is previewed, undone, redone and written on save", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();

    await contains(numberInput("paragraph-margin-top")).edit("8");
    await expect.waitForSteps(['preview user_values.scss {"paragraph-margin-top":"8px"}']);
    expect(getPreviewedValue("paragraph-margin-top")).toBe("8px");

    // Nothing pending anymore: the saved CSS is back, nothing to compile.
    await contains(".o_hb_snippets_top_actions button[data-icon='undo']").click();
    expect(getPreviewedValue("paragraph-margin-top")).toBe("");
    expect(":iframe style.o_theme_preview_css").toHaveCount(0);

    await contains(".o_hb_snippets_top_actions button[data-icon='redo']").click();
    await expect.waitForSteps(['preview user_values.scss {"paragraph-margin-top":"8px"}']);
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
    await expect.waitForSteps(['preview user_values.scss {"paragraph-margin-top":"8px"}']);
    expect(queryFirst(linkSelector).disabled).toBe(true);
    // In the bundle's place, before the stylesheets that come after it.
    expect(queryFirst(linkSelector).nextElementSibling).toHaveClass("o_theme_preview_css");

    await contains(".o_hb_snippets_top_actions button[data-icon='undo']").click();
    expect(queryFirst(linkSelector).disabled).toBe(false);
    expect(":iframe style.o_theme_preview_css").toHaveCount(0);
});

test("theme tab: the latest preview CSS wins", async () => {
    const firstCSS = Promise.withResolvers();
    const responses = [firstCSS.promise, ":root { --paragraph-margin-top: 12px; }"];
    onRpc("/website/theme_preview_css", () => responses.shift());
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
    const responses = [":root {}", ":root {}", undoCSS.promise];
    onRpc("/website/theme_preview_css", () => responses.shift());
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

// Each kind of value has its own pending values.
const DISCARDED_CHANGES = {
    value: {
        change: () => contains(numberInput("paragraph-margin-top")).edit("8"),
        preview: 'preview user_values.scss {"paragraph-margin-top":"8px"}',
    },
    color: {
        change: async () => {
            await contains(".o_hb_theme_color_slider_btn").click();
            await contains(
                ".o_hb_sliding_panel button.o_we_color_preview[title='Primary']"
            ).click();
            await contains(".o_popover .solid-tab").click();
            await contains(".o_popover [data-color='#FF0000']").click();
        },
        preview: 'preview user_color_palette.scss {"o-color-1":"#FF0000"}',
    },
    palette: {
        change: async () => {
            await contains(".o_hb_theme_color_slider_btn").click();
            await contains(".o_theme_tab [data-icon='palette']").click();
            await contains(
                `[data-action-value="'default-light-1'"] .o_hb_color_palette_card span`
            ).click();
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
    await expect.waitForSteps(['preview user_values.scss {"paragraph-margin-top":"8px"}']);
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
    await contains(".o_hb_sliding_panel button.o_we_color_preview[title='Primary']").click();
    await contains(".o_popover .solid-tab").click();
    await contains(".o_popover [data-color='#FF0000']").click();
    await expect.waitForSteps([
        'preview user_values.scss {"paragraph-margin-top":"8px"}',
        'preview user_values.scss {"paragraph-margin-top":"8px"} user_color_palette.scss {"o-color-1":"#FF0000"}',
    ]);

    await saveWebsite();
    expect.verifySteps([
        `${USER_VALUES} {"paragraph-margin-top":"8px"}`,
        `${PALETTE_URL} {"o-color-1":"#FF0000"}`,
    ]);
});
