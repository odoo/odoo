import { onMounted, onWillUnmount, proxy } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue } from "@html_editor/utils/formatting";
import { _t } from "@web/core/l10n/translation";
import { useBus } from "@web/core/utils/hooks";

export class ThemeColorsOption extends BaseOptionComponent {
    static template = "website.ThemeColorsOption";
    static dependencies = ["themeTab"];
    setup() {
        super.setup();
        this.isMobileBeforeThemeColorsPreview = null;
        this.palettes = this.getPalettes();
        this.colorPresetToShow = this.env.colorPresetToShow;
        this.grays = this.dependencies.themeTab.getGrays();
        this.state = useDomState(() => ({
            presets: this.getPresets(),
        }));
        this.websiteContext = proxy(this.services.website.context);
        useBus(this.services.website.bus, "CLOSE-THEME-COLORS-PREVIEW", () =>
            this.closeThemeColorsPreview()
        );
        onMounted(() => {
            this.iframeDocument = document.querySelector("iframe").contentWindow.document;
            this.state.presets = this.getPresets();
            this.colorPresetToShow = null;
        });
        onWillUnmount(() => this.closeThemeColorsPreview());
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

    get showThemeColorsPreview() {
        return this.websiteContext.showThemeColorsPreview;
    }

    openThemeColorsPreview() {
        const { context } = this.services.website;
        if (context.showThemeColorsPreview) {
            this.closeThemeColorsPreview();
            return;
        }
        this.isMobileBeforeThemeColorsPreview = context.isMobile;
        context.showThemeColorsPreview = true;
        context.isMobile = false;
    }

    closeThemeColorsPreview() {
        const { context } = this.services.website;
        if (!context.showThemeColorsPreview) {
            return;
        }
        context.showThemeColorsPreview = false;
        if (this.isMobileBeforeThemeColorsPreview !== null) {
            context.isMobile = this.isMobileBeforeThemeColorsPreview;
            this.isMobileBeforeThemeColorsPreview = null;
        }
    }
}
