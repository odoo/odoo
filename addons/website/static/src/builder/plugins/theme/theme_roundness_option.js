import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import {
    convertNumericToUnit,
    getCSSVariableValue,
    getHtmlStyle,
} from "@html_editor/utils/formatting";

export const BORDER_RADIUS_MULTIPLIERS = {
    "border-radius": 1,
    "border-radius-sm": 0.8,
    "border-radius-lg": 1.12,
};

const EPSILON = 0.01;

export class ThemeRoundnessOption extends BaseOptionComponent {
    static template = "website.ThemeRoundnessOption";
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

    const baseRadius = parseFloat(getCSSVariableValue("border-radius", style));
    const value = parseFloat(getCSSVariableValue(variable, style));

    const expectedValue = toFixedPixel(baseRadius * BORDER_RADIUS_MULTIPLIERS[variable], style);
    return Math.abs(value - expectedValue) >= EPSILON;
}

export function toFixedPixel(remValue, htmlStyle) {
    const pxValue = convertNumericToUnit(remValue, "rem", "px", htmlStyle);
    const roundedPxValue = Math.round(pxValue * 10) / 10;
    return convertNumericToUnit(roundedPxValue, "px", "rem", htmlStyle);
}
