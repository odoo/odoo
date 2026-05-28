import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { Rules } from "../core/rules_models";

const STYLE_CONTEXT_PROPERTIES = ["font-size", "font-weight", "line-height"];

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
        this.textStyleRules = new Rules();
        const textRules = this.textStyleRules.forPlugin(ContextStylePlugin.id);
        for (const propertyName of STYLE_CONTEXT_PROPERTIES) {
            textRules.allow(propertyName);
        }
    }

    /**
     * Return a style context where non-specified values are set to their
     * computed value.
     */
    getContextStyleInfo(element) {
        const styleInfo = this.filterStyleInfo(
            this.getRawStyleInfo(this.config.referenceDocument.body),
            element,
            this.textStyleRules
        );
        for (const propertyName of STYLE_CONTEXT_PROPERTIES) {
            if (!styleInfo.has(propertyName)) {
                styleInfo.setProperty(
                    propertyName,
                    this.getStylePropertyValue(element, propertyName)
                );
            }
        }
        return styleInfo;
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(ContextStylePlugin.id, ContextStylePlugin);
