import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { BuilderFontFamilyPicker } from "@html_builder/core/building_blocks/builder_fontfamilypicker";
import { BuilderButton } from "@html_builder/core/building_blocks/builder_button";
import { getCSSVariableValue } from "@html_editor/utils/formatting";
import { CustomizeWebsiteVariableAction } from "../customize_website_plugin";
import { FONT_VARIABLES_TO_RESET } from "../font/font_plugin";

export class ThemeFontFamilyOption extends BaseOptionComponent {
    static template = "website.ThemeFontFamilyOption";
    static props = {
        cssVariable: String,
        buttonIcon: String,
        buttonTitle: String,
    };
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
