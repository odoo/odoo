import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    mockThemeRpcs,
    PALETTE_URL,
    saveWebsite,
    setupWebsiteBuilder,
    USER_VALUES_URL,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

// A palette switch is previewed and written on save.
const PALETTE_PREVIEW = `preview user_values.scss {"color-palettes-name":"'default-light-1'"}`;
const PALETTE_SAVED = `${USER_VALUES_URL} {"color-palettes-name":"'default-light-1'"}`;
const COLOR_PREVIEW = 'preview user_color_palette.scss {"o-color-1":"#FF0000"}';

async function switchPalette(name = "default-light-1") {
    await contains(".o_theme_tab [data-icon='palette']").click();
    await contains(`[data-action-value="'${name}'"] .o_hb_color_palette_card span`).click();
}

async function openColors(options, content = "") {
    await setupWebsiteBuilder(content, options);
    await contains(".o_hb_snippets_tabs button[data-name=theme]").click();
    await contains(".o_hb_tab_content .o_hb_theme_color_slider_btn").click();
}

async function setPrimaryColor() {
    await contains(".o_hb_sliding_panel button.o_we_color_preview[title='Primary']").click();
    await contains(".o_popover .solid-tab").click();
    await contains(".o_popover [data-color='#FF0000']").click();
    await expect.waitForSteps([COLOR_PREVIEW]);
}

const CUSTOMIZED_COLORS = { styleContent: 'body { --has-customized-colors: "true"; }' };

test("theme tab: warning on palette change", async () => {
    mockThemeRpcs();
    await openColors(CUSTOMIZED_COLORS);
    await switchPalette();
    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog .btn-secondary").click();
    expect(".o_dialog").toHaveCount(0);
    await switchPalette();
    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog .btn-primary").click();
    await expect.waitForSteps([PALETTE_PREVIEW]);
    await saveWebsite();
    expect.verifySteps([PALETTE_SAVED]);
});

test("theme tab: no warning on palette change, the palette is previewed", async () => {
    mockThemeRpcs();
    await openColors();
    await switchPalette();
    expect(".o_dialog").toHaveCount(0);
    await expect.waitForSteps([PALETTE_PREVIEW]);
    await saveWebsite();
    expect.verifySteps([PALETTE_SAVED]);
});

test("theme tab: a palette switch drops the pending colors it resets", async () => {
    mockThemeRpcs();
    await openColors();
    await setPrimaryColor();
    await switchPalette();
    // The server resets the colors with the palette: none is left to write.
    await expect.waitForSteps([PALETTE_PREVIEW]);
    await saveWebsite();
    expect.verifySteps([PALETTE_SAVED]);
});

test("theme tab: a palette switch is undone and redone as one step", async () => {
    mockThemeRpcs();
    await openColors();
    await setPrimaryColor();
    await switchPalette();
    await expect.waitForSteps([PALETTE_PREVIEW]);

    await contains(".o_hb_snippets_top_actions button[data-icon='undo']").click();
    await expect.waitForSteps([COLOR_PREVIEW]);
    await contains(".o_hb_snippets_top_actions button[data-icon='redo']").click();
    await expect.waitForSteps([PALETTE_PREVIEW]);
    await saveWebsite();
    expect.verifySteps([PALETTE_SAVED]);
});

test("theme tab: a color changed after a palette switch is written after it", async () => {
    mockThemeRpcs();
    await openColors();
    await switchPalette();
    await expect.waitForSteps([PALETTE_PREVIEW]);
    await contains(".o_hb_sliding_panel button.o_we_color_preview[title='Primary']").click();
    await contains(".o_popover .solid-tab").click();
    await contains(".o_popover [data-color='#FF0000']").click();
    await expect.waitForSteps([
        `${PALETTE_PREVIEW} user_color_palette.scss {"o-color-1":"#FF0000"}`,
    ]);
    await saveWebsite();
    expect.verifySteps([PALETTE_SAVED, `${PALETTE_URL} {"o-color-1":"#FF0000"}`]);
});
