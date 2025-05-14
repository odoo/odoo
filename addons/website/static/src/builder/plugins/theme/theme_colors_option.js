import { onMounted } from "@odoo/owl";
import { getCSSVariableValue, getThemePresets } from "@html_builder/utils/utils_css";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class ThemeColorsOption extends BaseOptionComponent {
    static template = "website.ThemeColorsOption";
    static props = {};
    setup() {
        super.setup();
        this.palettes = this.getPalettes();
        this.iframeStyle = null;
        this.state = useDomState(() => ({
            presets: this.getPresets(),
        }));
        onMounted(() => {
            this.iframeStyle = this.env.editor.document.defaultView.getComputedStyle(
                this.env.editor.document.documentElement
            );
            this.state.presets = this.getPresets();
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

    getPresets() {
        return getThemePresets(this.iframeStyle);
    }
}
