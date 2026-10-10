import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue } from "@html_editor/utils/formatting";
import { ThemeFontFamilyOption } from "./theme_fontfamily_option";
import { ThemeFontWeightOption } from "./theme_font_weight_option";

export class ThemeButtonOption extends BaseOptionComponent {
    static template = "website.ThemeButtonOption";
    static components = {
        ThemeFontFamilyOption,
        ThemeFontWeightOption,
    };

    setup() {
        super.setup();
        const htmlStyle = this.env.editor.document.defaultView.getComputedStyle(
            this.env.getEditingElement()
        );
        this.state = useDomState(() => ({
            isRadiusSpecified: (variable) =>
                getCSSVariableValue(variable, htmlStyle) !==
                getCSSVariableValue(variable.replace("btn-", ""), htmlStyle),
        }));
    }
}
