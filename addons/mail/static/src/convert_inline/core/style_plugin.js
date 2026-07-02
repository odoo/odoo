import { Plugin } from "../plugin";
// import { withSequence } from "@html_editor/utils/resource";
import { parseCssText, parseSelector } from "@mail/convert_inline/css_parsers";
import { registry } from "@web/core/registry";
import { StyleInfo } from "./style_models";

export class StylePlugin extends Plugin {
    static id = "style";
    static dependencies = ["measurementSnapshot", "responsive"];
    static shared = ["getRawStyleInfo"];
    resources = {
        on_load_reference_content_handlers: this.loadAllFonts.bind(this),
        on_layout_dimensions_updated_handlers: this.onLayoutDimensionsUpdated.bind(this),
        on_parse_layout_with_dimensions_handlers: this.registerCSSRules.bind(this),
    };

    setup() {
        this.layoutToRuleInfos = new Map();
        this.layoutToStyleInfo = new Map();
    }

    onLayoutDimensionsUpdated(layoutDimensions) {
        this.layoutDimensions = layoutDimensions;
    }

    /**
     * @param {Object} [layoutDimensions]
     * @returns {WeakMap} elementToBlocks for requested layoutDimensions
     */
    getNodeToRuleInfos(layoutDimensions = this.layoutDimensions) {
        if (!this.layoutToRuleInfos.has(layoutDimensions)) {
            this.layoutToRuleInfos.set(layoutDimensions, new WeakMap());
        }
        return this.layoutToRuleInfos.get(layoutDimensions);
    }

    getNodeToStyleInfo(layoutDimensions = this.layoutDimensions) {
        if (!this.layoutToStyleInfo.has(layoutDimensions)) {
            this.layoutToStyleInfo.set(layoutDimensions, new WeakMap());
        }
        return this.layoutToStyleInfo.get(layoutDimensions);
    }

    loadAllFonts() {
        return this.config.referenceDocument.fonts.ready;
    }

    computeRuleInfo(complexSelector, rawRule) {
        if (!rawRule.style) {
            return;
        }
        const styleInfo = this.convertToStyleInfo(rawRule.style);
        if (styleInfo.size === 0) {
            return;
        }
        return {
            rawRule,
            complexSelector,
            styleInfo,
        };
    }

    computeDynamicValues(element, styleInfo) {
        let computedStyle;
        for (const [propertyName, propertyInfo] of styleInfo) {
            // TODO EGGMAIL: using the computed value is not equivalent
            // to resolving the calc|var, (e.g. line-height can be defined
            // without units and multiplied by the font-height, but the
            // computed value will be in px). A CSS parser would be
            // needed for full accuracy. Avoid using `calc` as much as
            // possible, as mail clients like outlook may not properly
            // interpret computed values as declared values. In case of bug
            // use MSO-specific style values to force it to use computed
            // values (e.g. mso-line-height-rule:exactly; for line-height).
            const simpleVarValue = this.getSimpleVarValue(
                propertyInfo.value,
                element,
                computedStyle
            );
            if (simpleVarValue !== undefined) {
                propertyInfo.value = simpleVarValue;
            } else if (
                propertyInfo.value.includes("calc(") ||
                propertyInfo.value.includes("var(")
            ) {
                // TODO EGGMAIL: Fix approximation: calc( or var( may be
                // part of a legit value, and other css functions may be
                // invalid for a given mail client
                computedStyle ??= this.getComputedStyle(element);
                propertyInfo.value = computedStyle.getPropertyValue(propertyName);
            }
        }
    }

    /**
     * Recursively try to identify simple var values. Only support a single
     * var() without a default value. Recursively look at variables until a
     * satisfactory value is found. Other complex cases are not handled.
     */
    getSimpleVarValue(value, element, computedStyle) {
        const getSimpleVar = (value) => {
            const [, simpleVar] = value.trim().match(/^var\(\s*(--\w{1}[\w-]*)\s*\)$/) ?? [];
            return simpleVar;
        };
        const simpleVar = getSimpleVar(value);
        if (simpleVar) {
            computedStyle ??= this.getComputedStyle(element);
            value = computedStyle.getPropertyValue(simpleVar);
            const recursionValue = this.getSimpleVarValue(value, element, computedStyle);
            if (recursionValue === undefined) {
                if (value.includes("calc(") || value.includes("var(")) {
                    // TODO EGGMAIL: Fix approximation: calc( or var( may be
                    // part of a legit value (not as css function), and other
                    // css functions may be invalid for a given mail client
                    return;
                } else {
                    return value;
                }
            } else {
                return recursionValue;
            }
        }
    }

    computeStyleInfo(element) {
        const layoutDimensions = this.layoutDimensions;
        const nodeToStyleInfo = this.getNodeToStyleInfo(layoutDimensions);
        const ruleInfos = this.getNodeToRuleInfos(layoutDimensions).get(element);
        if (!ruleInfos) {
            const styleInfo = this.convertToStyleInfo(element.style);
            this.computeDynamicValues(element, styleInfo);
            nodeToStyleInfo.set(element, styleInfo);
            return styleInfo;
        }
        ruleInfos.sort((a, b) => {
            for (let i = 0; i < 3; i++) {
                const diff = a.complexSelector.specificity[i] - b.complexSelector.specificity[i];
                if (diff !== 0) {
                    return diff;
                }
            }
            return 0;
        });
        const styleInfo = new StyleInfo();
        // Start sequence at 1 because 0 is reserved for default values
        let sequence = 1;
        for (const ruleInfo of ruleInfos) {
            styleInfo.merge(ruleInfo.styleInfo, sequence);
            sequence++;
        }
        styleInfo.merge(this.convertToStyleInfo(element.style), sequence);
        this.computeDynamicValues(element, styleInfo);
        nodeToStyleInfo.set(element, styleInfo);
        return styleInfo;
    }

    /**
     * @param {HTMLElement} element
     * @param {Object} [layoutDimensions]
     */
    getRawStyleInfo(element, layoutDimensions = this.layoutDimensions) {
        const nodeToStyleInfo = this.getNodeToStyleInfo(layoutDimensions);
        let styleInfo;
        if (nodeToStyleInfo.has(element)) {
            styleInfo = nodeToStyleInfo.get(element);
        } else if (layoutDimensions !== this.layoutDimensions) {
            console.warn(
                `Cache miss: called "getRawStyleInfo" with mismatched layoutDimensions on element.
                To avoid additional expensive layout computations, pre-fetch the value during "on_parse_layout_with_dimensions_handlers"`,
                element
            );
            this.callWithDimensions(() => {
                styleInfo = this.computeStyleInfo(element);
            }, layoutDimensions);
        } else {
            styleInfo = this.computeStyleInfo(element);
        }
        return styleInfo;
    }

    /**
     * @param {CSSStyleDeclaration} style
     * @returns {StyleInfo}
     */
    convertToStyleInfo(style) {
        const styleInfo = new StyleInfo();
        const propertyNames = parseCssText(style.cssText).map((property) => property.name);
        for (const propertyName of propertyNames) {
            const value = style.getPropertyValue(propertyName);
            if (value) {
                styleInfo.setProperty(propertyName, value, style.getPropertyPriority(propertyName));
            }
        }
        return styleInfo;
    }

    /**
     * TODO EGGMAIL: docstring, function objectives:
     * - associate relevant rules with every reference node
     */
    registerCSSRule(complexSelector, rawRule) {
        const nodes = this.config.referenceDocument.querySelectorAll(complexSelector.selector);
        if (!nodes.length) {
            return;
        }
        const ruleInfo = this.computeRuleInfo(complexSelector, rawRule);
        if (!ruleInfo) {
            return;
        }
        const nodeToRuleInfos = this.getNodeToRuleInfos();
        for (const node of nodes) {
            if (nodeToRuleInfos.has(node)) {
                const ruleInfos = nodeToRuleInfos.get(node);
                ruleInfos.push(ruleInfo);
            } else {
                nodeToRuleInfos.set(node, [ruleInfo]);
            }
        }
    }

    /**
     * TODO EGGMAIL: should we support other type of rules?
     * Disclaimer, only supports STYLE, MEDIA, IMPORT rules
     * @returns {Array<CSSStyleRule>}
     */
    processRule(rule, processedSheets = new Set(), styleRules = []) {
        const win = this.config.referenceDocument.defaultView;
        if (rule.constructor.name === "CSSStyleRule" && rule.selectorText) {
            styleRules.push(rule);
        } else if (rule.constructor.name === "CSSMediaRule" && rule.conditionText) {
            if (win.matchMedia(rule.conditionText).matches) {
                for (const childRule of rule.cssRules) {
                    this.processRule(childRule, processedSheets, styleRules);
                }
            }
        } else if (
            rule.constructor.name === "CSSImportRule" &&
            rule.styleSheet &&
            !processedSheets.has(rule.styleSheet)
        ) {
            processedSheets.add(rule.styleSheet);
            try {
                for (const childRule of rule.styleSheet.cssRules) {
                    this.processRule(childRule, processedSheets, styleRules);
                }
            } catch (e) {
                console.warn("Can't read the css rules of: " + rule.styleSheet.href, e);
            }
        }
        return styleRules;
    }

    /**
     * Parse through the given document stylesheets, preprocess(*) them and return
     * the result as an array of objects, each containing a selector string , a
     * style object and a specificity number. Preprocessing involves grouping
     * whatever rules can be grouped together and precomputing their specificity so
     * as to sort them appropriately.
     *
     * TODO EGGMAIL: new docstring, function objectives:
     * - parse all stylesheets
     * - identify applicable rules
     * - split rules into parts on selector groups (comma-separated)
     *
     * @returns {Object[]} Array<{selector: string;
     *                            style: {[styleName]: string};
     *                            specificity: Array<Number>;}>
     */
    registerCSSRules() {
        if (this.layoutToRuleInfos.has(this.layoutDimensions)) {
            return;
        }
        const doc = this.config.referenceDocument;
        const processedSheets = new Set();
        for (const sheet of [...doc.styleSheets, ...doc.adoptedStyleSheets]) {
            if (processedSheets.has(sheet)) {
                continue;
            }
            processedSheets.add(sheet);

            let rules;
            try {
                rules = sheet.cssRules;
            } catch (e) {
                console.warn("Can't read the css rules of: " + sheet.href, e);
                continue;
            }
            for (const rule of rules || []) {
                const styleRules = this.processRule(rule, processedSheets);
                for (const styleRule of styleRules) {
                    const selectorList = parseSelector(styleRule.selectorText);
                    for (const complexSelector of selectorList) {
                        if (
                            !this.checkPredicates(
                                "is_blocked_rule_selector_predicates",
                                complexSelector
                            )
                        ) {
                            this.registerCSSRule(complexSelector, styleRule);
                        }
                    }
                }
            }
        }
    }
}

registry.category("mail-html-conversion-core-plugins").add(StylePlugin.id, StylePlugin);
