import { onMounted, onWillUnmount, signal } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { _t } from "@web/core/l10n/translation";
import { isColorGradient } from "@web/core/utils/colors";
import { CustomizeWebsiteColorAction } from "../customize_website_plugin";
import { computeColorPresetPreview, parseColor } from "./color_preset_preview";
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

/**
 * Same as `customizeWebsiteColor` for the colors of a color preset, but
 * previewed live and only written on save. The colors the preset compiles
 * into are computed for all presets (see `color_preset_preview.js`).
 */
export class PreviewWebsiteColorPresetAction extends CustomizeWebsiteColorAction {
    static id = "previewWebsiteColorPreset";
    // Drop the parent's `preview = false` and blocking `withCustomHistory`.
    setup() {}
    apply({ params: { mainParam: color, gradientColor, nullValue = "null" }, value }) {
        const customizeWebsite = this.dependencies.customizeWebsite;
        // Same split as the parent: a gradient resets the color and the other
        // way around.
        const gradientValue = gradientColor && isColorGradient(value) ? value : "";
        const { url, finalColors } = customizeWebsite.getColorsCustomization(
            { [color]: gradientValue ? "" : value },
            { resetCcOnEmpty: !gradientValue }
        );
        const style = getHtmlStyle(this.document);
        const toColor = (cssColor) =>
            cssColor &&
            parseColor(
                cssColor.startsWith("var(") ? getCSSVariableValue(cssColor, style) : cssColor
            );
        const constants = {
            bodyBg: toColor(getCSSVariableValue("body-bg", style)),
            contrastLight: toColor(getCSSVariableValue("white", style)),
            contrastDark: toColor(getCSSVariableValue("900", style)),
            minContrastRatio: parseFloat(getCSSVariableValue("min-contrast-ratio", style)),
            primary: toColor(getCSSVariableValue("primary", style)),
            secondary: toColor(getCSSVariableValue("secondary", style)),
        };
        const cssValues = {};
        for (let index = 1; index <= 5; index++) {
            const setColors = getCSSVariableValue(`o-cc${index}-set`, style).slice(1, -1).split(" ");
            const preset = {};
            for (const key of PRESET_COLORS) {
                const name = `o-cc${index}-${key}`;
                const isSet = key === "bg" || setColors.includes(key);
                const pendingValue =
                    name in finalColors ? finalColors[name] : customizeWebsite.getPendingValue(name, url);
                let cssColor = isSet ? getCSSVariableValue(name, style) : "";
                if (pendingValue !== undefined) {
                    // A named color (e.g. `'o-color-1'`) is printed as a
                    // variable.
                    cssColor = [nullValue, ""].includes(pendingValue)
                        ? ""
                        : pendingValue.replace(/^'(.*)'$/, "var(--$1)");
                }
                preset[key] = toColor(cssColor);
            }
            // A reset background shows the last saved one until save.
            preset.bg ||= toColor(getCSSVariableValue(`o-cc${index}-bg`, style));
            Object.assign(cssValues, computeColorPresetPreview(index, preset, constants));
            // The gradient covers the background color (`none` to hide a saved
            // one).
            const gradientName = `o-cc${index}-bg-gradient`;
            const savedGradient = getCSSVariableValue(gradientName, style).replace(/^'(.*)'$/, "$1");
            let gradient = savedGradient;
            if (gradientName === gradientColor) {
                gradient = gradientValue || (savedGradient && "none");
            } else if (customizeWebsite.getPendingValue(gradientName) !== undefined) {
                gradient = customizeWebsite.getPendingValue(gradientName);
                gradient = gradient === nullValue ? savedGradient && "none" : gradient;
            }
            cssValues[gradientName] = gradient;
        }
        if (gradientColor) {
            customizeWebsite.previewWebsiteVariables(
                { [gradientColor]: gradientValue || nullValue },
                nullValue,
                { [gradientColor]: cssValues[gradientColor] }
            );
        }
        customizeWebsite.previewWebsiteVariables(finalColors, nullValue, cssValues, url);
    }
}
