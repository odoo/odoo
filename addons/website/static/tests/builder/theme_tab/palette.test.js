import { expect, queryFirst, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    mockThemeRpcs,
    PALETTE_URL,
    saveWebsite,
    setupWebsiteBuilder,
    USER_VALUES_URL,
} from "@website/../tests/builder/website_helpers";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

// A palette switch is previewed and written on save, with the gradients the
// server resets anyway.
const PALETTE_SAVED = `${USER_VALUES_URL} ${JSON.stringify({
    "color-palettes-name": "'default-light-1'",
    ...Object.fromEntries([1, 2, 3, 4, 5].map((i) => [`o-cc${i}-bg-gradient`, "null"])),
})}`;

async function switchPalette(name = "default-light-1") {
    await contains(".o_theme_tab [data-icon='palette']").click();
    await contains(`[data-action-value="'${name}'"] .o_hb_color_palette_card span`).click();
}

async function openColors(options, content = "") {
    await setupWebsiteBuilder(content, options);
    await contains(".o_hb_snippets_tabs button[data-name=theme]").click();
    await contains(".o_hb_tab_content .o_hb_theme_color_slider_btn").click();
}

const CUSTOMIZED_COLORS = { styleContent: 'body { --has-customized-colors: "true"; }' };

function getPaletteColor(name) {
    return getComputedStyle(document.documentElement)
        .getPropertyValue(`--o-palette-${name}-o-color-1`)
        .trim();
}

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
    expect.verifySteps([]);
    await saveWebsite();
    expect.verifySteps([PALETTE_SAVED]);
});

test("theme tab: no warning on palette change, the palette is previewed", async () => {
    mockThemeRpcs();
    await openColors();
    await switchPalette();
    expect(".o_dialog").toHaveCount(0);
    // The palette's colors are printed in the builder's document.
    expect(queryFirst(":iframe html").style.getPropertyValue("--o-default-o-color-1")).toBe(
        getPaletteColor("default-light-1")
    );
    expect.verifySteps([]);
    await saveWebsite();
    expect.verifySteps([PALETTE_SAVED]);
});

test("theme tab: a palette switch is undone and redone as one step", async () => {
    mockThemeRpcs();
    await openColors();
    const rootStyle = queryFirst(":iframe html").style;
    await switchPalette();
    const switchedStyle = rootStyle.cssText;
    expect(rootStyle.getPropertyValue("--color-palettes-name")).toBe("'default-light-1'");

    await contains(".o_hb_snippets_top_actions button[data-icon='undo']").click();
    expect(rootStyle.getPropertyValue("--color-palettes-name")).toBe("");
    expect(rootStyle.getPropertyValue("--o-default-o-color-1")).toBe("");
    await contains(".o_hb_snippets_top_actions button[data-icon='redo']").click();
    expect(rootStyle.cssText).toBe(switchedStyle);
    await saveWebsite();
    expect.verifySteps([PALETTE_SAVED]);
});

test("theme tab: after a palette switch, an area the palette gives no preset has none", async () => {
    mockThemeRpcs();
    await openColors({
        // The saved palette gives the copyright a preset, the new one none.
        styleContent: ":root { --copyright: 5; }",
        footerContent: `<footer id="bottom" class="o_footer">
            <div class="o_footer_copyright">Copyright</div></footer>`,
    });
    await switchPalette();
    expect(":iframe .o_footer_copyright").toHaveAttribute("data-o-cc-area", "copyright");
    expect(queryFirst(":iframe .o_footer_copyright").className).not.toMatch(/o_cc\d/);
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
    await contains(".o_hb_snippets_tabs").hover();
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
    await contains(".o_hb_sliding_panel button.o_we_color_preview[title='Primary']").click();
    await contains(".o_popover .solid-tab").click();
    await contains(".o_popover [data-color='#FF0000']").click();
    await switchPalette("default-light-1");
    expect(".o_dialog").toHaveCount(1);
});

test("theme tab: a shape with its default colors follows a palette switch once saved", async () => {
    mockThemeRpcs();
    onRpc("ir.ui.view", "save", () => {
        expect.step("view");
        return true;
    });
    await openColors(
        {},
        `<section data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"o-color-5"}}'>
            <div class="o_we_shape o_html_builder_Connections_01"/>
        </section>`
    );
    await switchPalette();
    // Its image comes from the compiled CSS, which follows the palette once
    // saved: the page is left as is.
    expect(queryFirst(":iframe .o_we_shape").style.backgroundImage).toBe("");
    await saveWebsite();
    expect.verifySteps([PALETTE_SAVED]);
});

test("theme tab: a palette switch keeps the areas' saved colors", async () => {
    mockThemeRpcs();
    await openColors({
        styleContent: `:root {
            --o-user-color-keys: "menu footer-custom";
            --o-user-menu: "3"; --o-user-footer-custom: "o-color-2";
            --footer-gradient: linear-gradient(red, blue);
        }`,
    });
    await switchPalette();
    expect(".o_dialog").toHaveCount(0);
    await saveWebsite();
    expect.verifySteps([
        `${USER_VALUES_URL} ${JSON.stringify({
            "color-palettes-name": "'default-light-1'",
            ...Object.fromEntries([1, 2, 3, 4, 5].map((i) => [`o-cc${i}-bg-gradient`, "null"])),
            "footer-gradient": "linear-gradient(red, blue)",
        })}`,
        `${PALETTE_URL} {"menu":"3","footer-custom":"'o-color-2'"}`,
    ]);
});
