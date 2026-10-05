import { expect, queryFirst, test } from "@odoo/hoot";
import { waitForNone } from "@odoo/hoot-dom";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

// A palette switch is previewed and written on save, with the gradients the
// server resets anyway.
const PALETTE_SAVED = `/website/static/src/scss/options/user_values.scss ${JSON.stringify({
    "color-palettes-name": "'default-light-1'",
    ...Object.fromEntries([1, 2, 3, 4, 5].map((i) => [`o-cc${i}-bg-gradient`, "null"])),
    ...Object.fromEntries(
        ["menu", "menu-secondary", "footer", "copyright", "breadcrumb"].map((name) => [
            `${name}-gradient`,
            "null",
        ])
    ),
})}`;

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
    onRpc("/website/theme_computed_colors", () => ({ values: {}, gates: {} }));
}

async function switchPalette(name = "default-light-1") {
    await contains(".o_theme_tab [data-icon='palette']").click();
    await contains(`[data-action-value="'${name}'"] .o-color-palette-card span`).click();
}

async function openColors(options) {
    await setupWebsiteBuilder("", options);
    await contains(".o-snippets-tabs button[data-name=theme]").click();
    await contains(".o-tab-content .o-hb-theme-color-slider-btn").click();
}

const CUSTOMIZED_COLORS = { styleContent: 'body { --has-customized-colors: "true"; }' };

function getPaletteColor(name) {
    return getComputedStyle(document.documentElement)
        .getPropertyValue(`--o-palette-${name}-o-color-1`)
        .trim();
}

async function save() {
    await contains(".o-snippets-top-actions [data-action='save']").click();
    await waitForNone(".o-snippets-top-actions");
}

test("theme tab: warning on palette change", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("", {
        styleContent: 'body { --has-customized-colors: "true"; }',
    });
    await contains(".o-snippets-tabs button[data-name=theme]").click();
    await contains(".o-tab-content .o-hb-theme-color-slider-btn").click();
    await switchPalette();
    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog .btn-secondary").click();
    expect(".o_dialog").toHaveCount(0);
    await switchPalette();
    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog .btn-primary").click();
    expect.verifySteps([]);
    await save();
    expect.verifySteps([PALETTE_SAVED]);
});

test("theme tab: no warning on palette change, the palette is previewed", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");
    await contains(".o-snippets-tabs button[data-name=theme]").click();
    await contains(".o-tab-content .o-hb-theme-color-slider-btn").click();
    await switchPalette();
    expect(".o_dialog").toHaveCount(0);
    // The palette's colors are printed in the builder's document.
    const color = getComputedStyle(document.documentElement)
        .getPropertyValue("--o-palette-default-light-1-o-color-1")
        .trim();
    expect(queryFirst(":iframe html").style.getPropertyValue("--o-default-o-color-1")).toBe(color);
    expect.verifySteps([]);
    await save();
    expect.verifySteps([PALETTE_SAVED]);
});

test("theme tab: hovering a palette previews it, without asking", async () => {
    mockThemeRpcs();
    await openColors(CUSTOMIZED_COLORS);
    await contains(".o_theme_tab [data-icon='palette']").click();
    const rootStyle = queryFirst(":iframe html").style;
    await contains(`.o-dropdown-item[data-action-value="'default-light-2'"]`).hover();
    expect(".o_dialog").toHaveCount(0);
    expect(rootStyle.getPropertyValue("--o-default-o-color-1")).toBe(
        getPaletteColor("default-light-2")
    );
    await contains(".o-snippets-tabs").hover();
    expect(rootStyle.getPropertyValue("--o-default-o-color-1")).toBe("");
    expect.verifySteps([]);
});

test("theme tab: after a palette switch, only colors changed since make it ask", async () => {
    mockThemeRpcs();
    await openColors(CUSTOMIZED_COLORS);
    await switchPalette("default-light-1");
    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog .btn-primary").click();
    // The switch resets the customizations: nothing left to lose.
    await switchPalette("default-light-2");
    expect(".o_dialog").toHaveCount(0);
    await contains(".hb-sliding-panel button.o_we_color_preview[title='Primary']").click();
    await contains(".o_popover .solid-tab").click();
    await contains(".o_popover [data-color='#FF0000']").click();
    await switchPalette("default-light-1");
    expect(".o_dialog").toHaveCount(1);
});
