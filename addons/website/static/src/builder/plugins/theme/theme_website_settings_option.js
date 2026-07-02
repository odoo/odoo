import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { ImageSize } from "@html_builder/plugins/image/image_size";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";

export const BORDER_RADIUS_MULTIPLIERS = {
    "border-radius": 1,
    "border-radius-sm": 0.8,
    "border-radius-lg": 1.12,
};

const EPSILON = 0.0001;

export class ThemeWebsiteSettingsOption extends BaseOptionComponent {
    static template = "website.ThemeWebsiteSettingsOption";
    static components = { ImageSize };
    static dependencies = ["customizeWebsite"];

    setup() {
        super.setup();
        this.state = useDomState(() => ({
            isCustomized: {
                "border-radius-sm": isBorderRadiusCustomized("border-radius-sm", this.document),
                "border-radius-lg": isBorderRadiusCustomized("border-radius-lg", this.document),
            },
        }));
    }
}

export function isBorderRadiusCustomized(variable, doc) {
    const style = getHtmlStyle(doc);
    const value =
        parseFloat(getCSSVariableValue(variable, style)) / BORDER_RADIUS_MULTIPLIERS[variable];
    const reference = parseFloat(getCSSVariableValue("border-radius", style));
    return Math.abs(value - reference) >= EPSILON;
}
