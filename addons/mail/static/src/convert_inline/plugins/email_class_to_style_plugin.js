import { BasePlugin } from "@html_editor/base_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { parseSelector } from "@mail/convert_inline/css_selector_parser";
import { splitSelectorList } from "@mail/convert_inline/style_utils";
import { registry } from "@web/core/registry";
import { useShorthands } from "@mail/convert_inline/plugins/hooks";

// TODO EGGMAIL: review regex, maybe use (future) selector parser instead
const SELECTORS_IGNORE = /(^\*$|:hover|:before|:after|:active|:link|::|')|@page/;

export class StyleInfo extends Map {
    getPropertyValue(propertyName) {
        return this.get(propertyName)?.value ?? "";
    }
    getPropertyPriority(propertyName) {
        return this.get(propertyName)?.priority ?? "";
    }
    getPropertySequence(propertyName) {
        return this.get(propertyName)?.sequence ?? 0;
    }
}

export class EmailClassToStylePlugin extends BasePlugin {
    static id = "classToStyle";
    static dependencies = ["computeStyle"];
    static shared = ["getStyleInfo"];
    resources = {
        ignored_style_predicates: (propertyName, value) =>
            !value ||
            propertyName.startsWith("--") ||
            propertyName.includes("animation") ||
            propertyName.includes("-webkit") ||
            typeof value !== "string",
        reference_content_loaded_handlers: this.classToStyle.bind(this),
        template_node_created_handlers: withSequence(
            1,
            this.applyStyleInfoOnTemplateNode.bind(this)
        ),
    };

    setup() {
        useShorthands(this, "computeStyle", ["getComputedStyle"]);
        this.nodeToRules = new WeakMap();
    }

    classToStyle() {
        this.registerCSSRules();
    }

    /**
     * @param {Object} ruleInfo
     * @returns {Boolean} whether the ruleInfo contains relevant information for
     *          email html.
     */
    validateRuleStyle(ruleInfo) {
        if (!ruleInfo.rawRule.style) {
            return false;
        }
        ruleInfo.styleInfo = this.normalizeStyle(ruleInfo.rawRule.style);
        if (ruleInfo.styleInfo.size === 0) {
            return false;
        }
        this.computeSpecificity(ruleInfo);
        return true;
    }

    /**
     * Take a selector and return its specificity according to the w3 specification.
     *
     * @see https://www.w3.org/TR/selectors-4/#specificity
     * @param {string} selector
     */
    computeSpecificity(ruleInfo) {
        const selectorList = parseSelector(ruleInfo.selector);
        ruleInfo.specificity = selectorList.specificity;
    }

    computeDynamicValues(element, styleInfo) {
        let computedStyle;
        for (const [propertyName, propertyInfo] of styleInfo.entries()) {
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
                propertyInfo.value = computedStyle[propertyName];
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
            value = computedStyle[simpleVar];
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

    getStyleInfo(element) {
        const styleInfo = new StyleInfo();
        // - Assume that styleInfoSource has higher specificity than anything
        // currently in styleInfo.
        // - Handle property priority
        const copyOnStyleInfo = (styleInfoSource, sequence) => {
            for (const [propertyName, propertyInfo] of styleInfoSource.entries()) {
                if (
                    styleInfoSource.getPropertyPriority(propertyName) ||
                    !styleInfo.getPropertyPriority(propertyName)
                ) {
                    propertyInfo.sequence = sequence;
                    styleInfo.set(propertyName, propertyInfo);
                }
            }
        };
        const nodeRules = this.nodeToRules.get(element);
        let sequence = 1;
        if (!nodeRules) {
            copyOnStyleInfo(this.normalizeStyle(element.style), sequence);
            return styleInfo;
        }
        if (nodeRules.styleInfo) {
            return nodeRules.styleInfo;
        }
        nodeRules.ruleInfos.sort((a, b) => {
            for (let i = 0; i < 3; i++) {
                const diff = a.specificity[i] - b.specificity[i];
                if (diff !== 0) {
                    return diff;
                }
            }
            return 0;
        });
        for (const ruleInfo of nodeRules.ruleInfos) {
            copyOnStyleInfo(ruleInfo.styleInfo, sequence);
            sequence++;
        }
        copyOnStyleInfo(this.normalizeStyle(element.style), sequence);
        this.computeDynamicValues(element, styleInfo);
        const styleInfoEntries = [...styleInfo.entries()];
        // Sort styleInfo entries by sequence, so that style properties from
        // rules with higher specificity come at the end. This is necessary
        // because e.g. a longhand property with higher specificity should
        // overwrite what a shorthand property with lower specificity defines.
        styleInfoEntries.sort(
            ([, propertyInfoA], [, propertyInfoB]) =>
                propertyInfoA.sequence - propertyInfoB.sequence
        );
        nodeRules.styleInfo = new StyleInfo(styleInfoEntries);
        return nodeRules.styleInfo;
    }

    /**
     * Take a css style declaration return a "normalized" version of it (as a
     * standard object) for the purposes of emails. This means removing its styles
     * that are invalid, describe animations or aren't standard css (webkit
     * extensions).
     *
     * @param {CSSStyleDeclaration} style
     * @returns {StyleInfo}
     */
    normalizeStyle(style) {
        const styleInfo = new StyleInfo();
        for (const propertyName of style) {
            const value = style.getPropertyValue(propertyName);
            if (
                !this.getResource("ignored_style_predicates").some((predicate) =>
                    predicate(propertyName, value)
                )
            ) {
                styleInfo.set(propertyName, {
                    value,
                    priority: style.getPropertyPriority(propertyName),
                });
            }
        }
        return styleInfo;
    }

    /**
     * TODO EGGMAIL: docstring, function objectives:
     * - associate relevant rules with every reference node
     */
    registerCSSRule(selector, rawRule) {
        const reference = this.config.desktop.reference;
        const nodes = reference.querySelectorAll(selector);
        const ruleInfo = {
            selector,
            rawRule,
        };
        if (!nodes.length || !this.validateRuleStyle(ruleInfo)) {
            return;
        }
        for (const node of nodes) {
            const nodeRules = this.nodeToRules.get(node);
            if (!nodeRules) {
                this.nodeToRules.set(node, { ruleInfos: [ruleInfo] });
            } else {
                nodeRules.ruleInfos.push(ruleInfo);
            }
        }
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
     * - identify all general rules and media min-width: 768px rules
     * - split rules into parts on selector groups (comma-separated)
     *
     * @returns {Object[]} Array<{selector: string;
     *                            style: {[styleName]: string};
     *                            specificity: Array<Number>;}>
     */
    registerCSSRules() {
        const doc = this.config.desktop.document;
        for (const sheet of [...doc.styleSheets, ...doc.adoptedStyleSheets]) {
            let rules;
            try {
                rules = sheet.cssRules;
            } catch (e) {
                // TODO EGGMAIL: review error, when can it happen, should we console.warn
                console.warn("Can't read the css rules of: " + sheet.href, e);
                continue;
            }
            for (const rule of rules || []) {
                const subRules = [rule];
                const conditionText = rule.conditionText;
                // TODO EGGMAIL: review regex
                const minWidthMatch = conditionText && conditionText.match(/\(min-width *: *(\d+)/);
                const minWidth = minWidthMatch && +(minWidthMatch[1] || "0");
                if (minWidth && minWidth >= 768) {
                    // Medium min-width media queries should be included.
                    // eg., .container has a default max-width for all screens.
                    let mediaRules;
                    try {
                        // TODO EGGMAIL: investigate what "rule" is about when there are
                        // mediaRules, do we have to keep the original rule?
                        // Conversely, what if it's not a mediaRules, can't we also have
                        // sub-cssRules?
                        mediaRules = rule.cssRules;
                        subRules.push(...mediaRules);
                    } catch (e) {
                        // TODO EGGMAIL: review error, when can it happen, should we console.warn
                        console.warn(
                            `Can't read the css rules of: ${sheet.href} (${conditionText})`,
                            e
                        );
                    }
                }
                for (const subRule of subRules) {
                    const selectorText = subRule.selectorText || "";
                    // Split selectors, making sure not to split at commas in parentheses.
                    for (const selector of splitSelectorList(selectorText)) {
                        if (selector && !SELECTORS_IGNORE.test(selector)) {
                            this.registerCSSRule(selector.trim(), subRule);
                        }
                    }
                }
            }
        }
    }

    /**
     * When a reference element is cloned, its StyleInfo is inlined on the
     * clone (templateNode).
     */
    applyStyleInfoOnTemplateNode({ nodeInfo, templateNode }) {
        const referenceNode = nodeInfo.referenceNode;
        if (
            templateNode.nodeType !== Node.ELEMENT_NODE ||
            referenceNode === this.config.reference
        ) {
            // The reference element itself is not part of the email, so its
            // style is irrelevant. Non-element nodes don't have a style
            // attribute.
            return;
        }
        const styleInfo = this.getStyleInfo(referenceNode);
        for (const propertyName of styleInfo.keys()) {
            templateNode.style.setProperty(
                propertyName,
                styleInfo.getPropertyValue(propertyName),
                styleInfo.getPropertyPriority(propertyName)
            );
        }
    }
}

registry
    .category("mail-html-conversion-plugins")
    .add(EmailClassToStylePlugin.id, EmailClassToStylePlugin);
