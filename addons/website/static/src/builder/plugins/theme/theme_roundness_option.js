import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { convertValueToUnit } from "@html_builder/utils/utils_css";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { proxy, useListener } from "@odoo/owl";

const BORDER_RADIUS_MULTIPLIERS = {
    "border-radius-sm": 0.75,
    "border-radius-lg": 1.5,
};

const EPSILON = 0.0001;

export class ThemeRoundnessOption extends BaseOptionComponent {
    static template = "website.ThemeRoundnessOption";

    setup() {
        super.setup();
        this.state = proxy({ customized: {} });
        const updateState = () => {
            for (const variable of ["border-radius-sm", "border-radius-lg"]) {
                this.state.customized[variable] = isBorderRadiusCustomized(variable, this.document);
            }
        };
        updateState();
        useListener(this.env.editorBus, "DOM_UPDATED", updateState);
    }
}

function isBorderRadiusCustomized(variable, doc) {
    const style = getHtmlStyle(doc);

    const baseRadius = convertValueToUnit(
        getCSSVariableValue("border-radius", style),
        "rem",
        style
    );
    const value = convertValueToUnit(getCSSVariableValue(variable, style), "rem", style);

    const expectedValue = baseRadius * BORDER_RADIUS_MULTIPLIERS[variable];
    return Math.abs(value - expectedValue) >= EPSILON;
}
