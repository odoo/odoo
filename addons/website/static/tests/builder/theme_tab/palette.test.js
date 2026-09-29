import { expect, queryFirst, test } from "@odoo/hoot";
import { waitForNone } from "@odoo/hoot-dom";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import { normalizeCSSColor } from "@web/core/utils/colors";

defineWebsiteModels();

const USER_VALUES = "/website/static/src/scss/options/user_values.scss";
// `default-light-1`'s first color.
const PALETTE_COLOR = "rgb(126, 209, 237)";
// The palette, and the preset gradients the server resets with it.
const PALETTE_WRITE = `${USER_VALUES} {${[1, 2, 3, 4, 5]
    .map((index) => `"o-cc${index}-bg-gradient":"null"`)
    .join(",")},"color-palettes-name":"'default-light-1'"}`;

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

function previewedColor() {
    return queryFirst(":iframe html").style.getPropertyValue("--o-preview-o-color-1");
}

async function switchPalette() {
    await contains(".o_theme_tab [data-icon='palette']").click();
    await contains(`[data-action-value="'default-light-1'"] .o-color-palette-card span`).click();
}

async function openColors() {
    await contains(".o-snippets-tabs button[data-name=theme]").click();
    await contains(".o-tab-content .o-hb-theme-color-slider-btn").click();
}

async function save() {
    await contains(".o-snippets-top-actions [data-action='save']").click();
    await waitForNone(".o-snippets-top-actions");
}

test("theme tab: a palette switch is previewed, undone, redone and written on save", async () => {
    mockThemeRpcs();
    // The palettes are printed by the compiled CSS.
    await setupWebsiteBuilder("", { loadIframeBundles: true });
    await openColors();

    await switchPalette();
    expect(".o_dialog").toHaveCount(0);
    expect(previewedColor()).toBe(PALETTE_COLOR);
    // The presets' cards show the colors computed from it, e.g. the button
    // text contrasting with the new first color.
    const buttonText = queryFirst(":iframe html").style.getPropertyValue(
        "--o-preview-o-cc1-btn-primary-color"
    );
    expect(buttonText).not.toBe("rgb(255, 255, 255)");
    const cardButtonText = getComputedStyle(document.documentElement).getPropertyValue(
        "--hb-cp-o-cc1-btn-primary-text"
    );
    expect(normalizeCSSColor(cardButtonText)).toBe(normalizeCSSColor(buttonText));

    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    expect(previewedColor()).toBe("");
    await contains(".o-snippets-top-actions button[data-icon='redo']").click();
    expect(previewedColor()).toBe(PALETTE_COLOR);
    expect.verifySteps([]);

    await save();
    expect.verifySteps([PALETTE_WRITE]);
});

test("theme tab: a palette switch replaces the previewed colors", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("", { loadIframeBundles: true });
    await openColors();
    await contains("button.o_we_color_preview[title='Primary']").click();
    await contains(".o_popover button.solid-tab").click();
    await contains(".o_popover button.o_color_button[data-color='#FF0000']").click();
    expect(previewedColor()).toBe("rgb(255, 0, 0)");

    await switchPalette();
    expect(previewedColor()).toBe(PALETTE_COLOR);

    // Only the palette is written: the server resets the colors.
    await save();
    expect.verifySteps([PALETTE_WRITE]);
});
