import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { DIRECTION_VARIANTS } from "../core/utils";
import { INDIRECT_CSS_PROPERTY_VALUES } from "../css_utils";

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

    // TODO EGGMAIL:
    // need to have a special ruleset for only border rules to isolate them

    getBorderStyleInfo(referenceNode) {
        // TODO EGGMAIL
        // need to apply border rules to styleInfo and then translate
        // border shorthands to their longhand counterparts
        // we can cheat a little in this case as the computed style will
        // have everything we need in the correct units, contrary to the spacing plugin
    }
}

registry.category("mail-html-conversion-core-plugins").add(BorderPlugin.id, BorderPlugin);
