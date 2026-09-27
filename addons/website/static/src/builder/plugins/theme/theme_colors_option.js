import { onMounted, onWillUnmount, signal } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { _t } from "@web/core/l10n/translation";
import { isColorGradient } from "@web/core/utils/colors";
import { CustomizeWebsiteColorAction } from "../customize_website_plugin";
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
const THEME_COLORS = ["primary", "secondary", "success", "info", "warning", "danger", "light", "dark"];

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
export function previewColors(action, { colors, gradientColor, gradientValue, nullValue }, cssValues = {}) {
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
        const name = cssColor.match(/^'(.+)'$|^var\(--(.+)\)$/)?.slice(1).find(Boolean);
        return name ? getColor(name) : parseColor(cssColor);
    };
    const presets = [1, 2, 3, 4, 5].map((index) => {
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
        isFullLayout: getCSSVariableValue("layout", style) === "'full'",
    });
    // The preset gradients cover their background color (`none` hides a
    // saved one).
    for (let index = 1; index <= 5; index++) {
        const name = `o-cc${index}-bg-gradient`;
        const savedGradient = getCSSVariableValue(name, style).replace(/^'(.*)'$/, "$1");
        let gradient = customizeWebsite.getPendingValue(name);
        if (name === gradientColor) {
            gradient = gradientValue || nullValue;
        }
        values[name] =
            gradient === undefined ? savedGradient : gradient === nullValue ? savedGradient && "none" : gradient;
    }
    Object.assign(values, cssValues);
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
 * Same as `customizeWebsiteColor` for the Theme tab colors, but previewed
 * live and only written on save.
 */
export class PreviewWebsiteColorAction extends CustomizeWebsiteColorAction {
    static id = "previewWebsiteColor";
    // Drop the parent's `preview = false` and blocking `withCustomHistory`.
    setup() {}
    apply({ params: { mainParam: color, colorType, gradientColor, nullValue = "null" }, value }) {
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
    }
}
