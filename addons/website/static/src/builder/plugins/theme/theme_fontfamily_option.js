import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { BuilderFontFamilyPicker } from "@html_builder/core/building_blocks/builder_fontfamilypicker";
import { BuilderButton } from "@html_builder/core/building_blocks/builder_button";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { PreviewWebsiteVariableAction } from "../customize_website_plugin";
import { FONT_VARIABLES_TO_RESET } from "../font/font_plugin";
import { getParsedWeight } from "./theme_font_weight_option";
import { useProps, t } from "@odoo/owl";

export class ThemeFontFamilyOption extends BaseOptionComponent {
    static template = "website.ThemeFontFamilyOption";
    props = useProps({
        cssVariable: t.string(),
        buttonIcon: t.string(),
        buttonIconClass: t.string().optional(),
        buttonTitle: t.string(),
    });
    static components = {
        BuilderFontFamilyPicker,
        BuilderButton,
    };

    setup() {
        super.setup();
        const htmlStyle = this.env.editor.document.defaultView.getComputedStyle(
            this.env.getEditingElement()
        );
        if (this.props.cssVariable === "headings-font") {
            this.state = useDomState(() => ({
                isFontSpecified:
                    getCSSVariableValue("headings-font", htmlStyle) !==
                    getCSSVariableValue("default-headings-font", htmlStyle),
            }));
        } else {
            this.state = useDomState(() => ({
                isFontSpecified: !!getCSSVariableValue("set-" + this.props.cssVariable, htmlStyle),
            }));
        }
    }
}

export class PreviewWebsiteFontFamilyAction extends PreviewWebsiteVariableAction {
    static id = "previewWebsiteFontFamily";
    static dependencies = ["customizeWebsite", "themeTab"];
    /**
     * The page only loads the fonts it uses: load the previewed one, so that
     * it renders and its weights are known.
     *
     * @returns {Promise<{ family: string, weights: { value: number }[] }|undefined>}
     *          the CSS font family and the font's weights
     */
    async load({ value }) {
        if (!value) {
            return;
        }
        const fontName = value.slice(1, -1);
        if (fontName === "SYSTEM_FONTS") {
            return { family: "var(--o-system-fonts)", weights: [] };
        }
        const style = getHtmlStyle(this.document);
        const fontCount = parseInt(getCSSVariableValue("number-of-fonts", style));
        for (let i = 1; i <= fontCount; i++) {
            if (getCSSVariableValue(`font-number-${i}`, style).slice(1, -1) !== fontName) {
                continue;
            }
            const url = getCSSVariableValue(`font-url-${i}`, style).slice(1, -1);
            if (url && !this.document.head.querySelector(`link[href="${url}"]`)) {
                const linkEl = this.document.createElement("link");
                linkEl.rel = "stylesheet";
                linkEl.href = url;
                const { promise, resolve } = Promise.withResolvers();
                linkEl.addEventListener("load", resolve);
                linkEl.addEventListener("error", resolve);
                this.document.head.append(linkEl);
                await promise;
            }
            break;
        }
        return {
            family: `${value}, var(--o-system-fonts)`,
            weights: await this.dependencies.themeTab.getFontWeights(value),
        };
    }
    apply({ params, value, loadResult }) {
        this.dependencies.customizeWebsite.previewWebsiteVariables(
            this.getVariablesToUpdate(params, value, loadResult?.weights),
            params.nullValue,
            { [params.mainParam]: loadResult?.family }
        );
    }
    /**
     * Keeps the font's weights that the new font has, and moves the others to
     * its nearest weight (which keeps light <= regular <= bold). They are only
     * reset when the new font's weights are unknown.
     *
     * @param {Object} params
     * @param {string} value
     * @param {{ value: number }[]} [weights] the new font's weights
     */
    getVariablesToUpdate(params, value, weights = []) {
        const nullValue = params.nullValue ?? "null";
        const variables = { [params.mainParam]: value };
        for (const resetVariable of FONT_VARIABLES_TO_RESET[params.mainParam] || []) {
            variables[resetVariable] = nullValue;
        }
        if (!weights.length) {
            return variables;
        }
        const customizeWebsite = this.dependencies.customizeWebsite;
        const values = weights.map((weight) => weight.value);
        for (const name of FONT_VARIABLES_TO_RESET[params.mainParam] || []) {
            // A weight set to "Auto" but not saved yet still shows the saved
            // one.
            const isPendingAuto = customizeWebsite.getPendingValue(name) === nullValue;
            const weight =
                !isPendingAuto && getParsedWeight(customizeWebsite.getWebsiteVariableValue(name));
            if (!weight) {
                // "Auto" stays.
                continue;
            }
            if (values.includes(weight)) {
                delete variables[name];
            } else {
                const nearest = values.reduce((best, candidate) =>
                    Math.abs(candidate - weight) < Math.abs(best - weight) ? candidate : best
                );
                variables[name] = `${nearest}`;
            }
        }
        return variables;
    }
}
// Alias, kept for compatibility with custom modules and themes.
export class CustomizeWebsiteFontFamilyAction extends PreviewWebsiteFontFamilyAction {
    static id = "customizeWebsiteFontFamily";
}
