import { onMounted } from "@odoo/owl";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue } from "@html_editor/utils/formatting";

export class ThemeColorsOption extends BaseOptionComponent {
    static template = "website.ThemeColorsOption";
    static props = {};
    setup() {
        super.setup();
        this.palettes = this.getPalettes();
        this.state = useDomState(() => ({
            presets: this.getPresets(),
        }));
        onMounted(() => {
            this.iframeDocument = document.querySelector("iframe").contentWindow.document;
            this.state.presets = this.getPresets();
        });
    }

    getPalettes() {
        const palettes = [];
        const style = window.getComputedStyle(document.documentElement);
        const uniquePaletteNames = new Set(getCSSVariableValue("palette-names", style).split(", "));
        const allPaletteNames = [...uniquePaletteNames].map((name) => name.replace(/'/g, ""));
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
}
