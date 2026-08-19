import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { CONTOUR_VARIANTS, DIRECTION_VARIANTS, INDIRECT_CSS_PROPERTY_VALUES } from "../core/utils";
import { StyleInfo } from "../core/style_models";

export class BorderPlugin extends Plugin {
    static id = "border";
    static dependencies = ["measurementSnapshot", "rules", "style"];
    static shared = ["hasVisibleBorder", "getBorderStyleInfo"];
    resources = {
        style_rules_processors: [[this.provideStyleRules.bind(this), BorderPlugin.id]],
    };

    provideStyleRules(rules) {
        // TODO EGGMAIL: borders can not be bigger than 8px -> fix all incorrect borders?
        rules.allow(/^border(-.*)?$/, {
            when: ({ propertyName }) =>
                propertyName !== "border-spacing" && propertyName !== "border-collapse",
        });
        rules.fix("border-color", {
            when: ({ propertyValue }) => INDIRECT_CSS_PROPERTY_VALUES.has(propertyValue),
            how: ({ referenceNode }) => this.getStylePropertyValue(referenceNode, "border-color"),
        });

        // Table
        const isTable = ({ referenceNode }) => referenceNode.nodeName === "TABLE";
        rules.allow("border-collapse", { when: isTable });
        rules.allow("border-spacing", { when: isTable });
    }

    hasVisibleBorder(element, layoutDimensions) {
        const computedStyle = this.getComputedStyle(element, null, layoutDimensions);
        return DIRECTION_VARIANTS.some((side) => {
            const width = parseFloat(computedStyle.getPropertyValue(`border-${side}-width`));
            const borderStyle = computedStyle.getPropertyValue(`border-${side}-style`);
            return width > 0 && borderStyle !== "none" && borderStyle !== "hidden";
        });
    }

    getBorderStyleInfo(referenceNode, layoutDimensions) {
        const styleInfo = new StyleInfo();
        const computedStyle = this.getComputedStyle(referenceNode, null, layoutDimensions);
        for (const side of DIRECTION_VARIANTS) {
            for (const feature of CONTOUR_VARIANTS) {
                const propertyName = `border-${side}-${feature}`;
                const propertyValue = computedStyle.getPropertyValue(propertyName);
                if (propertyValue) {
                    styleInfo.setProperty(propertyName, propertyValue);
                }
            }
        }
        return styleInfo;
    }
}

registry.category("mail-html-conversion-core-plugins").add(BorderPlugin.id, BorderPlugin);
