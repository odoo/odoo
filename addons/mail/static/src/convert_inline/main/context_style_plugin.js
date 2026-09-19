import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { Rules } from "../core/rules_models";
import { parseCssValue } from "../css_parsers";
import { areCSSColorEqual, isCSSColorTransparent } from "../core/utils";

const COMPUTABLE_TABLE_CONTEXT_STYLE_PROPERTIES = [
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
        on_measure_reference_content_handlers: this.captureBodyColor.bind(this),
        fix_raw_style_values_handlers: this.fixRemUnits.bind(this),
    };

    setup() {
        // TODO EGGMAIL: evaluate rules redundancy with filter_content_plugin
        // and where these context rules should be defined (probably here)
        this.tableContextStyleRules = new Rules();
        this.provideTableContextStyleRules();
        this.transparentFromReferenceDescendants = new Set();
        this.notTransparentFromReferenceDescendants = new Set();
    }

    captureBodyColor() {
        this.bodyColor = this.getStylePropertyValue(this.config.referenceDocument.body, "color");
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
            this.config.referenceDocument.documentElement,
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
        this.setTableContextLineHeight(styleInfo, element);
        this.setTableContextColor(styleInfo, element);
        return styleInfo;
    }

    setTableContextLineHeight(styleInfo, element) {
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
    }

    isTransparentFromReferenceDescendant(element) {
        if (this.transparentFromReferenceDescendants.has(element)) {
            return true;
        }
        if (this.notTransparentFromReferenceDescendants.has(element)) {
            return false;
        }
        let isTransparent, previousElement;
        let currentElement = element;
        const ancestors = new Set();
        do {
            const backgroundColor = this.getStylePropertyValue(currentElement, "background-color");
            isTransparent = isCSSColorTransparent(backgroundColor);
            ancestors.add(currentElement);
            previousElement = currentElement;
            currentElement = currentElement.parentElement;
        } while (
            isTransparent &&
            currentElement &&
            previousElement !== this.config.reference &&
            !this.notTransparentFromReferenceDescendants.has(currentElement) &&
            !this.transparentFromReferenceDescendants.has(currentElement)
        );
        if (
            isTransparent &&
            (previousElement === this.config.reference ||
                this.transparentFromReferenceDescendants.has(currentElement))
        ) {
            this.transparentFromReferenceDescendants =
                this.transparentFromReferenceDescendants.union(ancestors);
            return true;
        } else if (this.config.reference.contains(element)) {
            this.notTransparentFromReferenceDescendants =
                this.notTransparentFromReferenceDescendants.union(ancestors);
        }
        return false;
    }

    setTableContextColor(styleInfo, element) {
        // TODO EGGMAIL: there is an issue for tables, they have a triple-depth
        // var which resolves to "initial" which is not parsed properly
        // resulting in the computed color being applied
        // => table text will appear black in the chatter in dark mode
        // => find a solution for this case
        if (styleInfo.getPropertyValue("color")) {
            return;
        }
        const computedColor = this.getStylePropertyValue(element, "color");
        if (
            !areCSSColorEqual(computedColor, this.bodyColor) ||
            !this.isTransparentFromReferenceDescendant(element)
        ) {
            styleInfo.setProperty("color", computedColor);
        }
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(ContextStylePlugin.id, ContextStylePlugin);
