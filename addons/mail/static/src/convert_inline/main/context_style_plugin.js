import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { Rules } from "../core/rules_models";

const COMPUTABLE_TABLE_CONTEXT_STYLE_PROPERTIES = ["font-size", "font-weight"];
const TEXT_ALIGN_ALLOWED_VALUES = new Set(["right", "left", "center", "justify"]);
const TEXT_ALIGN_FIXABLE_VALUES = new Set(["start", "end"]);

/**
 * This plugin extracts css properties that can sometimes be overridden by
 * generic user agents (eg a web browser user agent has default css properties
 * for <table>). It is useful to restore style that would unintentionally be
 * modified by eg a wrapping table.
 * TODO EGGMAIL: maybe put in table_strategy_plugin
 */
export class ContextStylePlugin extends Plugin {
    static id = "contextStyle";
    static dependencies = ["measurementSnapshot", "rules", "style"];
    static shared = ["getTableContextStyleInfo"];

    setup() {
        // TODO EGGMAIL: evaluate rules redundancy with filter_content_plugin
        // and where these context rules should be defined (probably here)
        this.tableContextStyleRules = new Rules();
        this.provideTableContextStyleRules();
    }

    provideTableContextStyleRules() {
        const tableContextRules = this.tableContextStyleRules.forPlugin(ContextStylePlugin.id);
        for (const propertyName of COMPUTABLE_TABLE_CONTEXT_STYLE_PROPERTIES) {
            tableContextRules.allow(propertyName);
        }
        tableContextRules.allow("line-height");
        tableContextRules.allow("text-align", {
            when: ({ propertyValue }) => TEXT_ALIGN_ALLOWED_VALUES.has(propertyValue),
        });
        tableContextRules.fix("text-align", {
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

    getTableContextStyleInfo(element) {
        const styleInfo = this.filterStyleInfo(
            this.getRawStyleInfo(element),
            element,
            this.tableContextStyleRules
        );
        for (const propertyName of COMPUTABLE_TABLE_CONTEXT_STYLE_PROPERTIES) {
            if (!styleInfo.has(propertyName)) {
                styleInfo.setProperty(
                    propertyName,
                    this.getStylePropertyValue(element, propertyName)
                );
            }
        }
        if (styleInfo.getPropertyValue("line-height") === "") {
            // TODO EGGMAIL: fix simplification if necessary.
            // line-height should be extracted as a factor, not a px value.
            // if not specified for an element, default to the one specified
            // on the body (simplification). The correct solution would be a
            // recursive search for the first ancestor setting an explicit
            // line-height.
            const body = this.config.referenceDocument.body;
            const bodyStyleInfo = this.getRawStyleInfo(body);
            styleInfo.setProperty(
                "line-height",
                bodyStyleInfo.getPropertyValue("line-height") ||
                    this.getStylePropertyValue(body, "line-height")
            );
        }
        return styleInfo;
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(ContextStylePlugin.id, ContextStylePlugin);
