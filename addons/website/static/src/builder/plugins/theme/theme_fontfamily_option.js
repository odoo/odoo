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
     * The page only loads the fonts it uses: loads the previewed one, so that
     * it renders and its weights are known. A reset previews the font the
     * setting then follows.
     *
     * @returns {Promise<{ name: string, family: string, weights?: Object[] }>}
     */
    async load({ params: { mainParam: variable }, value }) {
        const customizeWebsite = this.dependencies.customizeWebsite;
        if (!value && variable === "buttons-font") {
            // Buttons inherit their font.
            return { name: "var(--font)", family: "initial" };
        }
        if (!value && variable !== "headings-font") {
            // A heading level follows the headings font.
            return { name: "var(--headings-font)", family: "var(--headings-font-family)" };
        }
        const name =
            value ||
            `'${
                customizeWebsite.getWebsiteVariableValue("default-headings-font") ||
                customizeWebsite.getWebsiteVariableValue("font")
            }'`;
        const style = getHtmlStyle(this.document);
        const fontCount = parseInt(getCSSVariableValue("number-of-fonts", style));
        for (let i = 1; i <= fontCount; i++) {
            if (getCSSVariableValue(`font-number-${i}`, style) !== name) {
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
            return {
                name,
                family: getCSSVariableValue(`font-family-${i}`, style),
                weights: await this.dependencies.themeTab.getFontWeights(name),
            };
        }
        return { name, family: "" };
    }
    apply({ params: { mainParam: variable, nullValue = "null" }, value, loadResult }) {
        const variables = { [variable]: value };
        // The font's family, as `website.scss` prints it.
        const familyVariable = variable === "font" ? "font-sans-serif" : `${variable}-family`;
        const previewValues = {
            [variable]: loadResult.name,
            [familyVariable]: loadResult.family,
        };
        if (variable !== "font") {
            previewValues[`set-${variable}`] = value ? loadResult.family : "initial";
        }
        // A weight the new font doesn't have moves to its nearest one. Unknown
        // weights (e.g. a system font): back to "Auto".
        const weights = (loadResult.weights || []).map(({ value }) => value);
        for (const weightVariable of FONT_VARIABLES_TO_RESET[variable] || []) {
            if (!weights.length) {
                variables[weightVariable] = nullValue;
                continue;
            }
            const weight = getParsedWeight(
                this.dependencies.customizeWebsite.getWebsiteVariableValue(weightVariable)
            );
            if (weight && !weights.includes(weight)) {
                variables[weightVariable] = `${weights.reduce((nearest, candidate) =>
                    Math.abs(candidate - weight) < Math.abs(nearest - weight) ? candidate : nearest
                )}`;
            }
        }
        this.dependencies.customizeWebsite.previewWebsiteVariables(
            variables,
            nullValue,
            previewValues
        );
    }
}
