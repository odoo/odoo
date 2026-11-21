import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useCustomizedVariables } from "./utils";
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
        this.state = useCustomizedVariables({
            "btn-border-radius": { derivedFrom: "border-radius" },
            "btn-border-radius-sm": { derivedFrom: "border-radius-sm" },
            "btn-border-radius-lg": { derivedFrom: "border-radius-lg" },
        });
    }
}
