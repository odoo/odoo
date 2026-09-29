import { onMounted, onWillUnmount, signal } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { _t } from "@web/core/l10n/translation";
import { isColorGradient } from "@web/core/utils/colors";
import {
    CustomizeWebsiteColorAction,
    CustomizeWebsiteVariableAction,
} from "../customize_website_plugin";
import { computeColorSystemPreview, parseColor } from "./color_system_preview";
import { ThemeColorsPreviewDialog } from "./theme_colors_preview_dialog";

const PRESET_COLORS = [
    "bg",
    "text",
    "headings",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "link",
    "btn-primary",
    "btn-primary-border",
    "btn-secondary",
    "btn-secondary-border",
];

export class ThemeColorsOption extends BaseOptionComponent {
    static template = "website.ThemeColorsOption";
    static dependencies = ["themeTab", "customizeWebsite"];
    isThemeColorsPreviewOpen = signal(false);

    setup() {
        super.setup();
        this.palettes = this.getPalettes();
        this.colorPresetToShow = this.env.colorPresetToShow;
        this.grays = this.dependencies.themeTab.getGrays();
        this.state = useDomState(() => ({
            presets: this.getPresets(),
        }));
        this.closeThemeColorsPreviewDialog = null;
        onMounted(() => {
            this.iframeDocument = document.querySelector("iframe").contentWindow.document;
            this.state.presets = this.getPresets();
            this.colorPresetToShow = null;
        });
        onWillUnmount(() => this.closeThemeColorsPreviewDialog?.());
    }

    getPalettes() {
        const palettes = [];
        const style = window.getComputedStyle(document.documentElement);
        const allPaletteNames = getCSSVariableValue("palette-names", style)
            .split(", ")
            .map((name) => name.replace(/'/g, ""));
        for (const paletteName of allPaletteNames) {
            const colors = Array.from({ length: 5 }, (_, index) =>
                getCSSVariableValue(`o-palette-${paletteName}-o-color-${index + 1}`, style)
            );
            const isDark =
                getCSSVariableValue(`o-palette-${paletteName}-is-dark`, style) === "true";
            palettes.push({
                name: paletteName,
                swatchColors: colors.slice(0, 2),
                backgroundColor: isDark ? colors[3] : colors[2],
                textColor: colors[4],
            });
        }
        return palettes;
    }

    getGrayTitle(grayCode) {
        return _t("Gray %(grayCode)s", { grayCode });
    }

    getPresets() {
        const presets = [];
        const unquote = (string) => string.substring(1, string.length - 1);
        for (let i = 1; i <= 5; i++) {
            const preset = {
                id: i,
                background: this.getColor(`o-cc${i}-bg`),
                backgroundGradient: unquote(this.getColor(`o-cc${i}-bg-gradient`)),
                text: this.getColor(`o-cc${i}-text`),
                headings: this.getColor(`o-cc${i}-headings`),
                primaryBtn: this.getColor(`o-cc${i}-btn-primary`),
                primaryBtnText: this.getColor(`o-cc${i}-btn-primary-text`),
                primaryBtnBorder: this.getColor(`o-cc${i}-btn-primary-border`),
                secondaryBtn: this.getColor(`o-cc${i}-btn-secondary`),
                secondaryBtnText: this.getColor(`o-cc${i}-btn-secondary-text`),
                secondaryBtnBorder: this.getColor(`o-cc${i}-btn-secondary-border`),
            };

            // TODO: check if this is necessary
            if (preset.backgroundGradient) {
                preset.backgroundGradient += ", url('/web/static/img/transparent.png')";
            }
            presets.push(preset);
        }
        return presets;
    }

    getColor(color) {
        if (!this.iframeDocument) {
            return "";
        }
        if (!this.iframeStyle) {
            this.iframeStyle = this.iframeDocument.defaultView.getComputedStyle(
                this.iframeDocument.documentElement
            );
        }
        return getCSSVariableValue(color, this.iframeStyle);
    }

    toggleThemeColorsPreview() {
        if (this.closeThemeColorsPreviewDialog) {
            this.closeThemeColorsPreviewDialog();
            return;
        }

        this.closeThemeColorsPreviewDialog = this.services.dialog.add(
            ThemeColorsPreviewDialog,
            {
                onIframeLoad: (previewDocument) => {
                    this.config.extraPreviewDocument = previewDocument;
                    this.dependencies.customizeWebsite.copyPreviewTo(previewDocument);
                },
            },
            {
                onClose: () => {
                    this.closeThemeColorsPreviewDialog = null;
                    this.config.extraPreviewDocument = null;
                    this.isThemeColorsPreviewOpen.set(false);
                },
            }
        );
        this.isThemeColorsPreviewOpen.set(true);
    }
}

const GRAY_COLORS = ["100", "200", "300", "400", "500", "600", "700", "800", "900"];
const PRESETS = [1, 2, 3, 4, 5];
const PALETTE_COLORS = PRESETS.map((index) => `o-color-${index}`);
const STATUS_COLORS = ["success", "info", "warning", "danger"];
const THEME_COLORS = ["primary", "secondary", ...STATUS_COLORS, "light", "dark"];

/**
 * Previews a change of the website colors, as values to write by file URL (see
 * `customizeWebsiteColors`). The colors the whole color system compiles into
 * are computed from all colors (see `color_system_preview.js`): the changed
 * ones, then the ones already previewed, then the saved ones. A color defined
 * as another one (printed as `--o-ref-<name>`) follows it.
 *
 * @param {BuilderAction} action
 * @param {Object} change
 * @param {Object<string, Object<string, string>>} change.colors
 * @param {string} [change.gradientColor] a color preset gradient
 * @param {string} [change.gradientValue]
 * @param {string} change.nullValue
 * @param {Object<string, string>} [cssValues] other preview-only values
 */
export function previewColors(action, change, cssValues = {}) {
    const { colors, gradientColor, gradientValue, nullValue } = change;
    const customizeWebsite = action.dependencies.customizeWebsite;
    const values = { ...computeColorPreviewValues(action, change), ...cssValues };
    if (gradientColor) {
        customizeWebsite.previewWebsiteVariables(
            { [gradientColor]: gradientValue || nullValue },
            nullValue,
            { [gradientColor]: values[gradientColor] }
        );
    }
    for (const [url, urlColors] of Object.entries(colors)) {
        customizeWebsite.previewWebsiteVariables(urlColors, nullValue, values, url);
    }
}

/**
 * The preview-only values of `previewColors` for a change (all of them, even
 * for no change).
 *
 * @param {BuilderAction} action
 * @param {Object} change see `previewColors`
 * @returns {Object<string, string>}
 */
export function computeColorPreviewValues(action, change) {
    const { colors, gradientColor, gradientValue, nullValue } = change;
    const customizeWebsite = action.dependencies.customizeWebsite;
    const style = getHtmlStyle(action.document);
    const getURL = (name) =>
        customizeWebsite.getColorsCustomization(
            {},
            {
                colorType: GRAY_COLORS.includes(name)
                    ? "gray"
                    : THEME_COLORS.includes(name)
                    ? "theme"
                    : "",
            }
        ).url;
    // The value to save for a color if it changed (empty when reset).
    const getNewValue = (name) => {
        const url = getURL(name);
        const value =
            name in (colors[url] || {})
                ? colors[url][name]
                : customizeWebsite.getPendingValue(name, url);
        return value === nullValue ? "" : value;
    };
    const resolvedColors = {};
    const getColor = (name) => {
        if (!(name in resolvedColors)) {
            const value = getNewValue(name);
            const reference = getCSSVariableValue(`o-ref-${name}`, style).slice(1, -1);
            resolvedColors[name] =
                value === undefined && reference
                    ? getColor(reference)
                    : // A reset color shows the saved one until save.
                      toColor(value || getCSSVariableValue(name, style));
        }
        return resolvedColors[name];
    };
    const toColor = (cssColor) => {
        // A named color (`'o-color-1'`, `var(--o-color-1)`) follows it.
        const name = cssColor
            .match(/^'(.+)'$|^var\(--(.+)\)$/)
            ?.slice(1)
            .find(Boolean);
        return name ? getColor(name) : parseColor(cssColor);
    };
    const presets = PRESETS.map((index) => {
        const setColors = getCSSVariableValue(`o-cc${index}-set`, style).slice(1, -1).split(" ");
        const preset = {};
        for (const key of PRESET_COLORS) {
            const name = `o-cc${index}-${key}`;
            const value = getNewValue(name);
            const isSet = value === undefined ? key === "bg" || setColors.includes(key) : !!value;
            preset[key] = isSet ? getColor(name) : null;
        }
        // A reset background shows the saved one until save.
        preset.bg ||= parseColor(getCSSVariableValue(`o-cc${index}-bg`, style));
        return preset;
    });
    const values = computeColorSystemPreview(getColor, presets, {
        minContrastRatio: parseFloat(getCSSVariableValue("min-contrast-ratio", style)),
        themeColorNames: THEME_COLORS.filter((name) => getCSSVariableValue(name, style)),
    });
    // The preset gradients cover their background color (`none` hides a
    // saved one).
    for (const index of PRESETS) {
        const name = `o-cc${index}-bg-gradient`;
        const savedGradient = getCSSVariableValue(name, style).replace(/^'(.*)'$/, "$1");
        let gradient = customizeWebsite.getPendingValue(name);
        if (name === gradientColor) {
            gradient = gradientValue || nullValue;
        }
        values[name] =
            gradient === undefined
                ? savedGradient
                : gradient === nullValue
                ? savedGradient && "none"
                : gradient;
    }
    return values;
}

/**
 * Same as `customizeWebsiteColor` for the Theme tab colors, but previewed
 * live and only written on save.
 */
export class PreviewWebsiteColorAction extends CustomizeWebsiteColorAction {
    static id = "previewWebsiteColor";
    // Drop the parent's `preview = false` and blocking `withCustomHistory`.
    setup() {}
    async apply({
        params: { mainParam: color, colorType, gradientColor, nullValue = "null" },
        value,
        isPreviewing,
    }) {
        // Same split as the parent: a gradient resets the color and the other
        // way around.
        const gradientValue = gradientColor && isColorGradient(value) ? value : "";
        const { url, finalColors } = this.dependencies.customizeWebsite.getColorsCustomization(
            { [color]: gradientValue ? "" : value },
            { colorType, resetCcOnEmpty: !gradientValue }
        );
        previewColors(this, {
            colors: { [url]: finalColors },
            gradientColor,
            gradientValue,
            nullValue,
        });
        if (!isPreviewing) {
            await updateColorsOutsideCSS(this, [color]);
        }
    }
}

/**
 * The colors a palette switch gives, by file URL (see `customizeWebsiteColors`)
 * and without the user's ones, which the server resets (see
 * `make_scss_customization`): the palette's, else the base palette's (see
 * `color_palettes.scss`), the base grays, and the references between colors.
 *
 * @param {BuilderAction} action
 * @param {string} paletteName
 * @returns {Object<string, Object<string, string>>}
 */
function getPaletteColors(action, paletteName) {
    const style = getHtmlStyle(action.document);
    const get = (name) => getCSSVariableValue(name, style);
    // The palettes and base grays are printed in the builder, as for the
    // palettes dropdown.
    const builderStyle = getComputedStyle(document.documentElement);
    const getBase = (name) => getCSSVariableValue(name, builderStyle);
    const getPaletteValue = (name) =>
        getBase(`o-palette-${paletteName}-${name}`) || getBase(`o-base-palette-${name}`);
    // A quoted name refers to another color.
    const resolve = (value) => {
        const name = value.match(/^'(.+)'$/)?.[1];
        if (!name) {
            return value;
        }
        const color = GRAY_COLORS.includes(name) ? getBase(`base-${name}`) : getPaletteValue(name);
        return resolve(color || get(name));
    };
    const getPaletteValues = (names) =>
        Object.fromEntries(names.map((name) => [name, getPaletteValue(name)]));
    const colors = getPaletteValues(PALETTE_COLORS);
    const presetColors = PRESETS.flatMap((index) =>
        PRESET_COLORS.map((key) => `o-cc${index}-${key}`)
    );
    for (const name of ["body", "input", ...presetColors]) {
        const value = getPaletteValue(name);
        colors[name] = resolve(value);
        colors[`o-ref-${name}`] = value.startsWith("'") ? value : "''";
    }
    for (const index of PRESETS) {
        // The preset's set colors (see `computeColorPreviewValues`).
        const keys = PRESET_COLORS.filter((key) => getPaletteValue(`o-cc${index}-${key}`));
        colors[`o-cc${index}-set`] = `'${keys.join(" ")}'`;
    }
    const themeColors = getPaletteValues(STATUS_COLORS);
    for (const [name, reference] of [
        ["primary", "'o-color-1'"],
        ["secondary", "'o-color-2'"],
    ]) {
        themeColors[name] = resolve(reference);
        themeColors[`o-ref-${name}`] = reference;
    }
    const grays = Object.fromEntries(GRAY_COLORS.map((name) => [name, getBase(`base-${name}`)]));
    const getURL = (colorType) =>
        action.dependencies.customizeWebsite.getColorsCustomization({}, { colorType }).url;
    return { [getURL("")]: colors, [getURL("theme")]: themeColors, [getURL("gray")]: grays };
}

/**
 * Switches the color palette, previewed live and only written on save.
 */
export class PreviewColorPaletteAction extends CustomizeWebsiteVariableAction {
    static id = "previewColorPalette";
    // Drop the parent's `preview = false` and blocking `withCustomHistory`.
    setup() {}
    async apply({ params: { mainParam: variable }, value, isPreviewing }) {
        const customizeWebsite = this.dependencies.customizeWebsite;
        customizeWebsite.previewSavedValues(getPaletteColors(this, value.slice(1, -1)));
        // The server resets the preset gradients too.
        customizeWebsite.previewWebsiteVariables(
            Object.fromEntries(PRESETS.map((index) => [`o-cc${index}-bg-gradient`, ""]))
        );
        customizeWebsite.previewWebsiteVariables(
            { [variable]: value },
            "null",
            computeColorPreviewValues(this, { colors: {}, nullValue: "null" })
        );
        if (!isPreviewing) {
            await updateColorsOutsideCSS(this, PALETTE_COLORS);
        }
    }
}

/**
 * Updates what carries the website colors outside of the CSS (e.g. the URL of
 * the shapes) from the previewed ones, in the same history step. On commit
 * only: it also updates the custom snippets, which a hover revert would not
 * undo.
 *
 * @param {BuilderAction} action
 * @param {string[]} colorNames the changed colors
 */
function updateColorsOutsideCSS(action, colorNames) {
    const handlers = action.getResource("on_website_color_updated_handlers");
    return Promise.allSettled(handlers.map((handler) => handler(colorNames)));
}
