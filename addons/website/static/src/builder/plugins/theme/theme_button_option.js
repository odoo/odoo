import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useVariablesDifferentFromGlobal } from "../utils";
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
        this.state = useVariablesDifferentFromGlobal(
            ["btn-border-radius", "btn-border-radius-sm", "btn-border-radius-lg"],
            this.document
        );
    }
}
