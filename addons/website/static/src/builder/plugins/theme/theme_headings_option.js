import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { ThemeFontFamilyOption } from "./theme_fontfamily_option";
import { ThemeFontWeightOption } from "./theme_font_weight_option";

export class ThemeHeadingsOption extends BaseOptionComponent {
    static template = "website.ThemeHeadingsOption";
    static components = {
        ThemeFontFamilyOption,
        ThemeFontWeightOption,
    };
}
