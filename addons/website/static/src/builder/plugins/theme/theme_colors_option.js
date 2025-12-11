import { onMounted } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue } from "@html_editor/utils/formatting";

export class ThemeColorsOption extends BaseOptionComponent {
    static template = "website.ThemeColorsOption";
    static dependencies = ["themeTab"];
    setup() {
        super.setup();
        this.panelTriggerLabel = _t("Colors");
        this.palettes = this.getPalettes();
        this.colorPresetToShow = this.env.colorPresetToShow;
        this.state = useDomState(() => ({
            presets: this.getPresets(),
            paletteColors: this.getPaletteColors(),
        }));
        this.grays = this.dependencies.themeTab.getGrays();
        onMounted(() => {
            this.iframeDocument = document.querySelector("iframe")?.contentWindow?.document;
            this.state.presets = this.getPresets();
            this.state.paletteColors = this.getPaletteColors();
            this.colorPresetToShow = null;
        });
    }

    getPalettes() {
        const palettes = [];
        const style = window.getComputedStyle(document.documentElement);
        const allPaletteNames = getCSSVariableValue("palette-names", style)
            .split(", ")
            .map((name) => name.replace(/'/g, ""));
        for (const paletteName of allPaletteNames) {
            const palette = {
                name: paletteName,
                colors: [],
            };
            [1, 3, 2].forEach((c) => {
                const color = getCSSVariableValue(`o-palette-${paletteName}-o-color-${c}`, style);
                palette.colors.push(color);
            });
            palettes.push(palette);
        }
        return palettes;
    }

    getPaletteColors() {
        const topStyle = this.getTopStyle();
        const hbCpColors = [1, 2, 3, 4, 5].map((index) =>
            getCSSVariableValue(`hb-cp-o-color-${index}`, topStyle)
        );
        if (hbCpColors.every((c) => !!c)) {
            return hbCpColors;
        }
        // Mirror the exact values used by the color pickers (o-color-1..5) as fallback.
        return [1, 2, 3, 4, 5].map((index) => this.getColor(`o-color-${index}`));
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
        const style = this.iframeDocument
            ? this.iframeStyle ||
              (this.iframeStyle = this.iframeDocument.defaultView.getComputedStyle(
                  this.iframeDocument.documentElement
              ))
            : this.getTopStyle();
        return getCSSVariableValue(color, style);
    }

    getTopStyle() {
        if (!this.topStyle) {
            this.topStyle = window.getComputedStyle(document.documentElement);
        }
        return this.topStyle;
    }
}
