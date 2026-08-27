import {
    isListElement,
    isListItemElement,
    isPhrasingContent,
    paragraphRelatedElements,
} from "@html_editor/utils/dom_info";
import { Plugin } from "../plugin";
import { StyleInfo } from "../core/style_models";
import { Rules } from "../core/rules_models";
import { registry } from "@web/core/registry";
import { parseCssValue } from "../css_parsers";
import { SpacingNode } from "./spacing_models";
import { withSequence } from "@html_editor/utils/resource";
import { ALLOWED_SPACING_UNITS, DIMENSIONS, DIRECTION_VARIANTS } from "../core/utils";

const { DESKTOP } = DIMENSIONS;

export const DEFAULT_SPACING_SEQUENCE = 20;
// TODO EGGMAIL: RTL + language check (vertical)
const SPACING_INLINE = {
    start: "left",
    end: "right",
};

/**
 * TODO EGGMAIL: handle vertical alignment? (should be done at a higher level),
 * eg vertical alignment necessary because a horizontal cell is bigger than
 * another.
 * TODO EGGMAIL: handle display-flex alignments as well? They don't use margin
 * but need centering => to investigate.
 * TODO EGGMAIL: about box-sizing: border-box; it is not supported by all
 * mail clients => the strategy is to never add padding and/or border on elements
 * with specified dimensions (height/width) => always use wrappers, in that case
 * there is no difference between content-box and border-box ; Add a warning when
 * an element has a padding or a border AND a specified dimension in the same
 * direction.
 */
export class SpacingPlugin extends Plugin {
    static id = "spacing";
    static dependencies = [
        "contextStyle",
        "measurementSnapshot",
        "referenceNode",
        "responsiveBlock",
        "rules",
        "style",
    ];
    static shared = [
        "getPaddingStyleInfo",
        "getMarginStyleInfo",
        "buildMarginNode",
        "buildPaddingNode",
        "hasMarginSpacing",
        "hasPaddingSpacing",
        "validateSpacingValue",
    ];
    resources = {
        on_parse_layout_with_dimensions_handlers: this.cacheSpacingStyleInfo.bind(this),
        reference_node_facts_processors: this.addSpacingFacts.bind(this),
        refine_layout_processors: withSequence(
            DEFAULT_SPACING_SEQUENCE,
            this.applyDefaultSpacing.bind(this)
        ),
        attribute_rules_processors: [[this.provideAttributeRules.bind(this), SpacingPlugin.id]],
        style_rules_processors: [[this.provideStyleRules.bind(this), SpacingPlugin.id]],
        fix_raw_style_values_handlers: this.fixSpacingInline.bind(this),
        fix_rem_units_overrides: this.fixSpacingRemUnits.bind(this),
        merge_fact_overrides: this.mergeSpacingInfo.bind(this),
    };

    setup() {
        this.marginStyleRules = new Rules();
        this.paddingStyleRules = new Rules();
        this.provideSpacingStyleRules();
    }

    fixSpacingInline({ element, propertyName, propertyInfo, styleInfo }) {
        if (!propertyName.match(/^(margin|padding)-inline(-(start|end))?$/)) {
            return false;
        }
        const values = this.decomposeSpacingShorthandValue(propertyInfo.value);
        if (values.length === 0 || values.length > 2) {
            return false;
        }
        const spacing = propertyName.startsWith("margin") ? "margin" : "padding";
        const ending = propertyName.split("-").at(-1);
        const sequence = propertyInfo.sequence;
        const priority = propertyInfo.priority;
        const indexByPropertyName = styleInfo.getIndexByPropertyName();
        const index = indexByPropertyName.get(propertyName);
        styleInfo.delete(propertyName);
        const fixedStyleInfo = new StyleInfo();
        if (values.length === 1) {
            if (ending === "inline") {
                for (const side in SPACING_INLINE) {
                    fixedStyleInfo.setProperty(
                        `${spacing}-${side}`,
                        values.at(0),
                        priority,
                        sequence
                    );
                }
            } else {
                fixedStyleInfo.setProperty(
                    `${spacing}-${ending}`,
                    values.at(0),
                    priority,
                    sequence
                );
            }
        } else if (values.length === 2) {
            let index = 0;
            for (const side in SPACING_INLINE) {
                fixedStyleInfo.setProperty(
                    `${spacing}-${side}`,
                    values.at(index),
                    priority,
                    sequence
                );
                index++;
            }
        }
        styleInfo.merge(fixedStyleInfo, { index });
        return true;
    }

    fixSpacingRemUnits({ element, propertyName, propertyInfo, styleInfo }) {
        let getStyleInfo;
        if (propertyName.startsWith("margin")) {
            getStyleInfo = this.getMarginStyleInfo.bind(this);
        } else if (propertyName.startsWith("padding")) {
            getStyleInfo = this.getPaddingStyleInfo.bind(this);
        } else {
            return;
        }
        const partialStyleInfo = new StyleInfo();
        partialStyleInfo.set(propertyName, propertyInfo);
        const decomposedStyleInfo = getStyleInfo(partialStyleInfo, element);
        if (decomposedStyleInfo.size === 0) {
            return;
        }
        const indexByPropertyName = styleInfo.getIndexByPropertyName();
        const index = indexByPropertyName.get(propertyName);
        styleInfo.delete(propertyName);
        const convertedStyleInfo = new StyleInfo();
        for (const [propertyName, propertyInfo] of decomposedStyleInfo) {
            if (this.convertRemPropertyInfoToPx({ element, propertyName, propertyInfo })) {
                convertedStyleInfo.set(propertyName, propertyInfo);
            }
        }
        styleInfo.merge(convertedStyleInfo, { index });
        return true;
    }

    addSpacingFacts(facts, { referenceNode }) {
        const rawStyleInfo = this.getRawStyleInfo(referenceNode, DESKTOP);
        const desktopMarginStyleInfo = this.getMarginStyleInfo(rawStyleInfo, referenceNode);
        const desktopPaddingStyleInfo = this.getPaddingStyleInfo(rawStyleInfo, referenceNode);
        return Object.assign(facts, { desktopMarginStyleInfo, desktopPaddingStyleInfo });
    }

    mergeSpacingInfo({ fact, isConstraint }) {
        if (isConstraint) {
            return;
        }
        // TODO EGGMAIL: maybe combine padding of ancestor with margin and padding of descendant?
        // currently margin of ancestor is preserved, and padding of descendant is preserved
        // which is ok as long as they have the same dimensions
        if (fact === "desktopMarginStyleInfo") {
            // Prevent override of desktopMarginStyleInfo:
            // use case is top -> down traversal, margin info of the ancestor is
            // kept.
            return true;
        }
    }

    ensureResponsiveElementWidth(styleInfo, referenceNode) {
        const widthInfo = styleInfo.get("width");
        if (widthInfo) {
            return;
        }
        // Enforce a responsive width based on its desktop width.
        const width = this.getStylePropertyValue(referenceNode, "width");
        styleInfo.setProperty("width", "100%");
        styleInfo.setProperty("max-width", width);
    }

    // TODO EGGMAIL NOW: generalize the content of this function, there are
    // multiple aspects to consider for the wrapping table:
    // - spacing
    // - horizontal centering (vertical centering does not happen on a spacing table, it should
    // happen more globally (and requires handling (TODO)))
    //
    buildMarginNode(emailNode, spacingNodeArgs = {}) {
        if (emailNode.layout.ancestorTag === "TABLE") {
            // TODO EGGMAIL: maybe move in a separate plugin handling table issues?
            const rootRef = emailNode.layout.getRef();
            const { number, unit } = parseCssValue(rootRef.styleInfo.getPropertyValue("width"));
            if (unit === "px" && number > 0) {
                spacingNodeArgs.refs ??= {};
                spacingNodeArgs.refs.root ??= {};
                spacingNodeArgs.refs.root.style ??= {};
                spacingNodeArgs.refs.root.style = StyleInfo.from(
                    spacingNodeArgs.refs.root.style
                ).merge(StyleInfo.from({ "table-layout": "fixed" }));
            }
        }
        const facts = emailNode.analysis.facts;
        // TODO EGGMAIL: discard negative paddings
        // for % values, use computed value in px (desktop mode) instead
        const marginNode = new SpacingNode(spacingNodeArgs);
        const marginLayout = marginNode.layout;
        const styleInfo = facts.desktopMarginStyleInfo;
        let isRelevant = false;
        const setAttributes = (options, ref) => {
            marginLayout.setAttributes(options, ref);
            isRelevant = true;
        };
        if (
            styleInfo.getPropertyValue("margin-left") === "auto" &&
            styleInfo.getPropertyValue("margin-right") === "auto"
        ) {
            setAttributes({ attributes: { align: "center" } });
            setAttributes({ attributes: { align: "center" } }, "cell");
        } else if (styleInfo.getPropertyValue("margin-left") === "auto") {
            // TODO EGGMAIL: consider RTL
            setAttributes({ attributes: { align: "right" } });
            setAttributes({ attributes: { align: "right" } }, "cell");
        } else if (styleInfo.getPropertyValue("margin-right") === "auto") {
            // TODO EGGMAIL: consider RTL
            setAttributes({ attributes: { align: "left" } });
            setAttributes({ attributes: { align: "left" } }, "cell");
        }
        const referenceNode = emailNode.firstReferenceNode;
        if (
            referenceNode &&
            this.isBlock(referenceNode) &&
            (styleInfo.getPropertyValue("margin-left") === "auto" ||
                styleInfo.getPropertyValue("margin-right") === "auto")
        ) {
            const styleInfo = emailNode.layout.getRef().styleInfo;
            // TODO EGGMAIL: need MSO fallback?s
            styleInfo.setProperty("display", "inline-block");
            this.ensureResponsiveElementWidth(styleInfo, referenceNode);
        }
        for (const side of DIRECTION_VARIANTS) {
            const value = styleInfo.getPropertyValue(`margin-${side}`);
            const { number, unit } = parseCssValue(value);
            if (number > 0 && (unit === "px" || unit === "em")) {
                // The margin spacing node is meant as a wrapper and replaces
                // static margin by padding on the main wrapper cell.
                setAttributes({ style: { [`padding-${side}`]: value } }, "cell");
            }
        }
        if (isRelevant) {
            const contextNode = this.getContextNode(emailNode);
            const context = { style: this.getTableContextStyleInfo(contextNode) };
            marginNode.layout.setAttributes(context, "cell");
            return marginNode;
        }
    }

    buildPaddingNode(emailNode, spacingNodeArgs = {}) {
        const facts = emailNode.analysis.facts;
        const paddingNode = new SpacingNode(spacingNodeArgs);
        const paddingLayout = paddingNode.layout;
        const styleInfo = facts.desktopPaddingStyleInfo;
        let isRelevant = false;
        const setAttributes = (options, ref) => {
            paddingLayout.setAttributes(options, ref);
            isRelevant = true;
        };
        for (const side of DIRECTION_VARIANTS) {
            const value = styleInfo.getPropertyValue(`padding-${side}`);
            const { number, unit } = parseCssValue(value);
            if (number > 0 && (unit === "px" || unit === "em")) {
                setAttributes({ style: { [`padding-${side}`]: value } }, "cell");
            }
        }
        if (isRelevant) {
            const contextNode = this.getContextNode(emailNode);
            const context = { style: this.getTableContextStyleInfo(contextNode) };
            paddingNode.layout.setAttributes(context, "cell");
            return paddingNode;
        }
    }

    hasPaddingSpacing(analysis) {
        return (
            analysis.facts.desktopPaddingStyleInfo &&
            analysis.facts.desktopPaddingStyleInfo.size !== 0
        );
    }

    hasMarginSpacing(analysis) {
        return (
            analysis.facts.desktopMarginStyleInfo &&
            analysis.facts.desktopMarginStyleInfo.size !== 0
        );
    }

    applyDefaultSpacing(layout, { emailNode }) {
        const contextNode = this.getContextNode(emailNode);
        const renderNode = this.config.referenceDocument.createElement(
            emailNode.layout.descendantTag
        );
        if (
            !this.isBlock(contextNode, { evaluateDisconnected: true }) ||
            isPhrasingContent(renderNode) ||
            // TODO EGGMAIL: are there cases where LI and UL elements have
            // necessary custom spacing? (list-group is already handled in list_strategy)
            isListElement(renderNode) ||
            isListItemElement(renderNode)
        ) {
            return layout;
        }
        if (
            this.hasMarginSpacing(emailNode.analysis) &&
            !paragraphRelatedElements.includes(layout.ancestorTag)
        ) {
            const marginNode = this.buildMarginNode(emailNode, {
                refs: { root: { style: { width: "100%" } } },
            });
            if (marginNode) {
                emailNode.marginNode = marginNode;
            }
        }
        if (this.hasPaddingSpacing(emailNode.analysis)) {
            const paddingNode = this.buildPaddingNode(emailNode, {
                refs: { root: { style: { width: "100%" } } },
            });
            if (paddingNode) {
                if (paragraphRelatedElements.includes(layout.descendantTag)) {
                    // inline style margin is allowed on paragraph related elements
                    // but not padding. To support padding, wrap the element in
                    // a spacing table (the reverse can not be done because a
                    // table inside a paragraph is illegal html).
                    emailNode.marginNode = paddingNode;
                } else {
                    emailNode.paddingNode = paddingNode;
                }
            }
        }
        return layout;
    }

    cacheSpacingStyleInfo() {
        const treeWalker = this.createReferenceTreeWalker({
            filter: (node) =>
                node.nodeType === Node.ELEMENT_NODE
                    ? NodeFilter.FILTER_ACCEPT
                    : NodeFilter.FILTER_REJECT,
        });
        let element = treeWalker.root;
        do {
            this.getRawStyleInfo(element);
        } while ((element = treeWalker.nextNode()));
    }

    decomposeSpacingShorthandValue(value) {
        const splitValue = value.split(" ");
        let values;
        if (splitValue.length === 1) {
            values = Array(4).fill(value, 0, 4);
        } else if (splitValue.length === 2) {
            values = [splitValue[0], splitValue[1], splitValue[0], splitValue[1]];
        } else if (splitValue.length === 3) {
            values = [splitValue[0], splitValue[1], splitValue[1], splitValue[2]];
        } else {
            values = splitValue;
        }
        return values;
    }

    getMarginStyleInfo(styleInfo, referenceNode) {
        return this.getSpacingStyleInfo(styleInfo, referenceNode, this.marginStyleRules);
    }

    getPaddingStyleInfo(styleInfo, referenceNode) {
        return this.getSpacingStyleInfo(styleInfo, referenceNode, this.paddingStyleRules);
    }

    /**
     * Returns a normalized spacing styleInfo containing only longhand css
     * properties. Only support simple padding/margin variants.
     *
     * @returns {StyleInfo}
     */
    getSpacingStyleInfo(styleInfo, referenceNode, rules) {
        const filteredStyleInfo = this.filterStyleInfo(styleInfo, referenceNode, rules);
        // TODO EGGMAIL: this is incomplete CSS value parsing, would be unnecessary
        // if we have a complete value parser.
        const longhandStyleInfo = new StyleInfo();
        const shorthandStyleInfo = new StyleInfo();
        const setShorthandPropertyValues = (propertyName, values, priority, sequence) => {
            DIRECTION_VARIANTS.forEach((suffix, index) => {
                const name = `${propertyName}-${suffix}`;
                shorthandStyleInfo.setProperty(name, values[index], priority, sequence);
            });
        };
        for (const [
            propertyName,
            { value, priority, sequence },
        ] of filteredStyleInfo.getSortedEntries()) {
            if (propertyName === "padding" || propertyName === "margin") {
                const values = this.decomposeSpacingShorthandValue(value);
                setShorthandPropertyValues(propertyName, values, priority, sequence);
            } else {
                longhandStyleInfo.setProperty(propertyName, value, priority, sequence);
            }
        }
        return shorthandStyleInfo.merge(longhandStyleInfo);
    }

    provideSpacingStyleRules() {
        const paddingRules = this.paddingStyleRules.forPlugin(SpacingPlugin.id);
        const marginRules = this.marginStyleRules.forPlugin(SpacingPlugin.id);
        // TODO EGGMAIL: support more spacing cases?
        paddingRules.allow(/^padding(-(top|right|bottom|left))?$/);
        marginRules.allow(/^margin(-(top|right|bottom|left))?$/);
    }

    validateSpacingValue({ propertyName, propertyValue }) {
        if (propertyName === "margin" || propertyName === "padding") {
            const values = this.decomposeSpacingShorthandValue(propertyValue);
            return values.every((value) => {
                const { number, unit } = parseCssValue(value);
                return (
                    number !== undefined &&
                    (number === 0 || (number > 0 && ALLOWED_SPACING_UNITS.has(unit)))
                );
            });
        } else {
            const { number, unit } = parseCssValue(propertyValue);
            return number === 0 || (number > 0 && ALLOWED_SPACING_UNITS.has(unit));
        }
    }

    provideAttributeRules(rules) {
        rules.require("cellpadding", {
            when: ({ referenceNode }) => referenceNode.nodeName === "TABLE",
            how: () => ({ attributeValue: "0" }),
        });
    }

    /**
     * Style rules for nodes that do not allow the default spacing.
     */
    provideStyleRules(rules) {
        // Allow paragraph-related elements to keep their top/bottom margins
        rules.allow(/^margin(-(top|bottom))?$/, {
            when: [
                ({ referenceNode }) => paragraphRelatedElements.includes(referenceNode.nodeName),
                this.validateSpacingValue.bind(this),
            ],
        });
        // allow inline phrasing content to have a positive margin
        rules.allow(/^margin(-(top|right|bottom|left))?$/, {
            when: [
                ({ referenceNode }) =>
                    !this.isBlock(referenceNode, { evaluateDisconnected: true }) ||
                    isPhrasingContent(referenceNode),
                this.validateSpacingValue.bind(this),
            ],
        });
        // allow inline phrasing content to have a positive padding if width is not 100%
        // of its container
        rules.allow(/^padding(-(top|right|bottom|left))?$/, {
            when: [
                ({ referenceNode }) =>
                    !this.isBlock(referenceNode, { evaluateDisconnected: true }) ||
                    isPhrasingContent(referenceNode),
                this.validateSpacingValue.bind(this),
                ({ referenceNode }) => {
                    const rawStyleInfo = this.getRawStyleInfo(referenceNode);
                    // TODO EGGMAIL: could be improved by computing the available space and ensuring
                    // the element + spacing is smaller than that (box-sizing: content-box issue)
                    // but this is still not perfect as the width can be changed by a window
                    // resize and the inline element can become too big with padding.
                    return rawStyleInfo.getPropertyValue("width") !== "100%";
                },
            ],
        });
        // HR can have a userAgent style which needs to be countered
        const isHR = ({ referenceNode }) => referenceNode.nodeName === "HR";
        // block HR margin no matter what, to make it "fail".
        rules.block(/^margin(-(top|right|bottom|left))?$/, { when: isHR });
        // HR margin is handled separately from the inline style by the spacing
        // plugin, but its inline style margin must be forced to 0.
        rules.require("margin", {
            when: isHR,
            how: () => ({ propertyValue: "0", propertyPriority: "important" }),
        });

        // blockquote (remove margin against useragent)
        const isBlockquote = ({ referenceNode }) => referenceNode.nodeName === "BLOCKQUOTE";
        rules.block(/^margin-(left|top|right)$/, { when: isBlockquote });
        rules.require("margin-left", {
            when: isBlockquote,
            how: () => ({ propertyValue: "0", propertyPriority: "important" }),
        });
        rules.require("margin-right", {
            when: isBlockquote,
            how: () => ({ propertyValue: "0", propertyPriority: "important" }),
        });
        rules.require("margin-top", {
            when: isBlockquote,
            how: () => ({ propertyValue: "0", propertyPriority: "important" }),
        });
    }
}

registry.category("mail-html-conversion-main-plugins").add(SpacingPlugin.id, SpacingPlugin);
