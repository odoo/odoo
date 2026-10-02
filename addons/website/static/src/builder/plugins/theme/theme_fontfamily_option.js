import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { BuilderFontFamilyPicker } from "@html_builder/core/building_blocks/builder_fontfamilypicker";
import { BuilderButton } from "@html_builder/core/building_blocks/builder_button";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { CustomizeWebsiteVariableAction } from "../customize_website_plugin";
import { FONT_VARIABLES_TO_RESET } from "../font/font_plugin";
import { useProps, t } from "@odoo/owl";

export class ThemeFontFamilyOption extends BaseOptionComponent {
    static template = "website.ThemeFontFamilyOption";
    props = useProps({
        cssVariable: t.string(),
        action: t.string().optional("previewWebsiteFontFamily"),
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

export class CustomizeWebsiteFontFamilyAction extends CustomizeWebsiteVariableAction {
    static id = "customizeWebsiteFontFamily";

    async apply({ params: { mainParam: variable, nullValue = "null" }, value }) {
        const variables = { [variable]: value };
        for (const resetVariable of FONT_VARIABLES_TO_RESET[variable] || []) {
            variables[resetVariable] = nullValue;
        }
        await this.dependencies.customizeWebsite.customizeWebsiteVariables(variables, nullValue);
    }
}

/**
 * The CSS variable that holds the family of a font setting (see the font
 * families printed in `website.scss`).
 *
 * @param {string} fontVariable e.g. "headings-font"
 */
function getFamilyVariable(fontVariable) {
    return fontVariable === "font" ? "font-sans-serif" : `${fontVariable}-family`;
}

export class PreviewWebsiteFontFamilyAction extends CustomizeWebsiteVariableAction {
    static id = "previewWebsiteFontFamily";
    // Drop the parent's `preview = false` and blocking `withCustomHistory`.
    setup() {}
    /**
     * The page only loads the fonts it uses: loads the previewed one, so that
     * it renders and its weights are known. A reset previews the font the
     * setting then follows.
     *
     * @returns {Promise<{ name: string, family: string }>}
     */
    async load({ params: { mainParam: variable }, value }) {
        const customizeWebsite = this.dependencies.customizeWebsite;
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
            return { name, family: style.getPropertyValue(`--font-family-${i}`) };
        }
        return { name, family: "" };
    }
    apply({ params: { mainParam: variable, nullValue = "null" }, value, loadResult }) {
        const variables = { [variable]: value };
        const previewValues = {
            [variable]: loadResult.name,
            [getFamilyVariable(variable)]: loadResult.family,
        };
        if (variable !== "font") {
            previewValues[`set-${variable}`] = value ? loadResult.family : "initial";
        }
        // The weights go back to "Auto", the font's weights may differ.
        for (const weightVariable of FONT_VARIABLES_TO_RESET[variable] || []) {
            variables[weightVariable] = nullValue;
            previewValues[weightVariable] = "initial";
        }
        this.dependencies.customizeWebsite.previewWebsiteVariables(
            variables,
            nullValue,
            previewValues
        );
    }
}
