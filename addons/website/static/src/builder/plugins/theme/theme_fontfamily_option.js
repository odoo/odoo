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

    async apply({ params, value }) {
        await this.dependencies.customizeWebsite.customizeWebsiteVariables(
            this.getVariablesToUpdate(params, value),
            params.nullValue
        );
    }
    getVariablesToUpdate({ mainParam: variable, nullValue = "null" }, value) {
        const variables = { [variable]: value };
        for (const resetVariable of FONT_VARIABLES_TO_RESET[variable] || []) {
            variables[resetVariable] = nullValue;
        }
        return variables;
    }
}

export class PreviewWebsiteFontFamilyAction extends CustomizeWebsiteFontFamilyAction {
    static id = "previewWebsiteFontFamily";
    // Drop the parent's `preview = false` and blocking `withCustomHistory`.
    setup() {}
    /**
     * The page only loads the fonts it uses: load the previewed one, so that
     * it renders and its weights are listed.
     *
     * @returns {Promise<string|undefined>} the CSS font family
     */
    async load({ value }) {
        if (!value) {
            return;
        }
        const fontName = value.slice(1, -1);
        if (fontName === "SYSTEM_FONTS") {
            return "var(--o-system-fonts)";
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
        return `${value}, var(--o-system-fonts)`;
    }
    apply({ params, value, loadResult }) {
        this.dependencies.customizeWebsite.previewWebsiteVariables(
            this.getVariablesToUpdate(params, value),
            params.nullValue,
            { [params.mainParam]: loadResult }
        );
    }
}
