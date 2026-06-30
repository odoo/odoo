import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { Rules } from "../core/rules_models";

const INHERITED_STYLE_CONTEXT_PROPERTIES = ["font-size", "font-weight", "line-height"];
const TEXT_ALIGN_ALLOWED_VALUES = new Set(["right", "left", "center", "justify"]);
const TEXT_ALIGN_FIXABLE_VALUES = new Set(["start", "end"]);

/**
 * This plugin extracts css properties that can sometimes be overridden by
 * generic user agents (eg a web browser user agent has default css properties
 * for <table>). It is useful to restore style that would unintentionally be
 * modified by eg a wrapping table.
 */
export class ContextStylePlugin extends Plugin {
    static id = "contextStyle";
    static dependencies = ["measurementSnapshot", "rules", "style"];
    static shared = ["getContextStyleInfo"];

    setup() {
        this.inheritedStyleRules = new Rules();
        const inheritedRules = this.inheritedStyleRules.forPlugin(ContextStylePlugin.id);
        for (const propertyName of INHERITED_STYLE_CONTEXT_PROPERTIES) {
            inheritedRules.allow(propertyName);
        }

        // TODO EGGMAIL: evaluate rules redundancy with filter_content_plugin
        // and where these context rules should be defined (probably here)
        this.styleRules = new Rules();
        const styleRules = this.styleRules.forPlugin(ContextStylePlugin.id);
        styleRules.allow("text-align", {
            when: ({ propertyValue }) => TEXT_ALIGN_ALLOWED_VALUES.has(propertyValue),
        });
        styleRules.fix("text-align", {
            when: ({ propertyValue }) => TEXT_ALIGN_FIXABLE_VALUES.has(propertyValue),
            how: ({ propertyValue }) => {
                // TODO EGGMAIL: consider RTL
                let value;
                if (propertyValue === "start") {
                    value = "left";
                } else if (propertyValue === "end") {
                    value = "right";
                }
                if (value) {
                    return { propertyValue: value };
                }
            },
        });
    }

    getContextStyleInfo(element) {
        return this.getInheritedContextStyleInfo(element).merge(
            this.getNonInheritedContextStyleInfo(element)
        );
    }

    /**
     * Return a style context where non-specified values are set to their
     * computed value.
     */
    getInheritedContextStyleInfo(element) {
        const styleInfo = this.filterStyleInfo(
            this.getRawStyleInfo(element),
            element,
            this.inheritedStyleRules
        );
        for (const propertyName of INHERITED_STYLE_CONTEXT_PROPERTIES) {
            if (!styleInfo.has(propertyName)) {
                styleInfo.setProperty(
                    propertyName,
                    this.getStylePropertyValue(element, propertyName)
                );
            }
        }
        return styleInfo;
    }

    getNonInheritedContextStyleInfo(element) {
        return this.filterStyleInfo(this.getRawStyleInfo(element), element, this.styleRules);
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(ContextStylePlugin.id, ContextStylePlugin);
