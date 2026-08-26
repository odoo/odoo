import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { Rules } from "../core/rules_models";
import { parseCssValue } from "../css_parsers";

const COMPUTABLE_TABLE_CONTEXT_STYLE_PROPERTIES = [
    "color",
    "font-size",
    "font-style",
    "font-weight",
    "text-align",
];
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
    static shared = [
        "convertRemPropertyInfoToPx",
        "convertRemValueToPx",
        "getContextNode",
        "getTableContextStyleInfo",
    ];
    resources = {
        fix_raw_style_values_overrides: this.fixRemUnits.bind(this),
    };

    setup() {
        // TODO EGGMAIL: evaluate rules redundancy with filter_content_plugin
        // and where these context rules should be defined (probably here)
        this.tableContextStyleRules = new Rules();
        this.provideTableContextStyleRules();
    }

    fixRemUnits({ element, propertyName, propertyInfo, styleInfo }) {
        if (!propertyInfo.value.includes("rem")) {
            return false;
        }
        if (
            this.delegateTo("fix_rem_units_overrides", {
                element,
                propertyName,
                propertyInfo,
                styleInfo,
            })
        ) {
            return true;
        }
        return this.convertRemPropertyInfoToPx({ element, propertyName, propertyInfo });
    }

    convertRemPropertyInfoToPx({ element, propertyName, propertyInfo }) {
        let pxValue = this.convertRemValueToPx(propertyInfo.value);
        if (pxValue === undefined) {
            // TODO EGGMAIL: this does not handle shorthand properties where
            // part of the value is in rem. To fix using fix_rem_units_overrides
            // when issues arise.
            pxValue = this.getStylePropertyValue(element, propertyName);
        }
        if (pxValue === "") {
            return false;
        }
        propertyInfo.value = pxValue;
        return true;
    }

    convertRemValueToPx(value) {
        const { number, unit } = parseCssValue(value);
        if (unit !== "rem") {
            return;
        }
        const rootFontSize = this.getStylePropertyValue(
            this.config.referenceDocument.body,
            "font-size"
        );
        const fontSizeValue = parseCssValue(rootFontSize);
        if (!fontSizeValue.number < 0 || fontSizeValue.unit !== "px") {
            return;
        }
        return `${fontSizeValue.number * number}px`;
    }

    provideTableContextStyleRules() {
        const tableContextRules = this.tableContextStyleRules.forPlugin(ContextStylePlugin.id);
        tableContextRules.allow("font-size");
        tableContextRules.allow("font-style");
        tableContextRules.allow("font-weight");
        tableContextRules.allow("line-height");
        tableContextRules.allow("color");
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

    getContextNode(emailNode) {
        let contextNode;
        let currentNode = emailNode;
        do {
            contextNode = currentNode.lastReferenceNode;
            currentNode = currentNode.parent;
        } while (currentNode && !contextNode);
        if (!contextNode) {
            contextNode = this.config.referenceDocument.body;
        }
        return contextNode;
    }

    getTableContextStyleInfo(element) {
        const rawStyleInfo = this.getRawStyleInfo(element);
        // TODO EGGMAIL: rethink what "COMPUTABLE_TABLE_CONTEXT_STYLE_PROPERTIES" means
        // -> we should probably have a value for each of the useragent overwriting rule
        for (const propertyName of [...COMPUTABLE_TABLE_CONTEXT_STYLE_PROPERTIES]) {
            if (!rawStyleInfo.has(propertyName)) {
                rawStyleInfo.setProperty(
                    propertyName,
                    this.getStylePropertyValue(element, propertyName)
                );
            }
        }
        const styleInfo = this.filterStyleInfo(rawStyleInfo, element, this.tableContextStyleRules);
        let lineHeight = styleInfo.getPropertyValue("line-height");
        if (lineHeight === "" && element.closest("table")) {
            let referenceNode = element;
            do {
                const rawStyleInfo = this.getStyleInfo(referenceNode);
                lineHeight = rawStyleInfo.getPropertyValue("line-height");
                referenceNode = referenceNode.parentElement;
            } while (!lineHeight && this.config.reference.contains(referenceNode));
            if (lineHeight) {
                styleInfo.setProperty("line-height", lineHeight);
            }
        }
        if (lineHeight === "") {
            // line-height should be extracted as a factor, not a px value.
            // if not specified for an element, default to the one specified
            // on the body (simplification).
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
