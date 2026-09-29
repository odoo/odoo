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
const USER_COLORS = "/website/static/src/scss/options/colors/user_color_palette.scss";
// `default-light-1`'s first color.
const PALETTE_COLOR = "rgb(126, 209, 237)";
// The palette, and the preset and area gradients the server resets with it.
const PALETTE_GRADIENTS = [
    ...[1, 2, 3, 4, 5].map((index) => `o-cc${index}-bg`),
    "menu",
    "menu-secondary",
    "footer",
    "copyright",
    "breadcrumb",
];
const paletteWrite = (gradients) =>
    `${USER_VALUES} {${gradients
        .map((name) => `"${name}-gradient":"null"`)
        .join(",")},"color-palettes-name":"'default-light-1'"}`;
const PALETTE_WRITE = paletteWrite(PALETTE_GRADIENTS);

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

const HEADER = `
    <header id="top" data-anchor="true" data-name="Header">
        <nav class="navbar navbar-light">
            <div id="o_main_nav" class="container o_main_nav"> content </div>
        </nav>
    </header>`;

async function pickHeaderPreset(index) {
    await contains(":iframe #wrapwrap > header").click();
    await contains("[data-label='Background'] .o_we_color_preview").click();
    await contains(`.o_popover button[data-color='o_cc${index}']`).click();
}

test("theme tab: an area color picked after a palette switch is written after it", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("", { loadIframeBundles: true, headerContent: HEADER });
    await openColors();
    await switchPalette();
    await pickHeaderPreset(5);
    // The header shows the new palette's fifth preset.
    const rootStyle = queryFirst(":iframe html").style;
    const presetBg = rootStyle.getPropertyValue("--o-preview-o-cc5-bg");
    expect(rootStyle.getPropertyValue("--o-preview-menu-bg")).toBe(presetBg);
    expect(":iframe header nav").toHaveStyle({ backgroundColor: presetBg });
    expect.verifySteps([]);

    // The palette first: the server resets the color files with it. The
    // header's gradient is reset by the header color.
    await save();
    expect.verifySteps([
        PALETTE_WRITE.replace(`"menu-gradient":"null"`, `"menu-gradient":"NULL"`),
        `${USER_COLORS} {"menu-custom":"NULL","menu":5}`,
    ]);
});

test("theme tab: a palette switch drops a previewed area color", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("", { loadIframeBundles: true, headerContent: HEADER });
    await pickHeaderPreset(5);
    await openColors();
    await switchPalette();
    expect(queryFirst(":iframe html").style.getPropertyValue("--menu")).not.toBe("5");

    // The header color's gradient reset was the first user value.
    await save();
    expect.verifySteps([
        paletteWrite(["menu", ...PALETTE_GRADIENTS.filter((name) => name !== "menu")]),
    ]);
});
