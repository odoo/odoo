import { paragraphRelatedElements } from "@html_editor/utils/dom_info";
import { DIMENSIONS } from "../hooks";
import { Plugin } from "../plugin";
import { StyleInfo } from "../core/style_models";
import { Rules } from "../core/rules_models";
import { registry } from "@web/core/registry";
import { parseCssValue } from "../css_parsers";
import { SpacingNode } from "./spacing_models";
import { withSequence } from "@html_editor/utils/resource";
import { DIRECTION_VARIANTS } from "../core/utils";

const { DESKTOP } = DIMENSIONS;

export const DEFAULT_SPACING_SEQUENCE = 20;

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
    ];
    resources = {
        on_parse_layout_with_dimensions_handlers: this.cacheSpacingStyleInfo.bind(this),
        reference_node_facts_processors: this.addSpacingFacts.bind(this),
        refine_layout_processors: withSequence(
            DEFAULT_SPACING_SEQUENCE,
            this.applyDefaultSpacing.bind(this)
        ),
        style_rules_processors: [[this.provideStyleRules.bind(this), SpacingPlugin.id]],
        merge_fact_overrides: this.mergeSpacingInfo.bind(this),
    };

    setup() {
        this.marginStyleRules = new Rules();
        this.paddingStyleRules = new Rules();
        this.provideSpacingStyleRules();
    }

    addSpacingFacts(facts, { referenceNode }) {
        const rawStyleInfo = this.getRawStyleInfo(referenceNode, DESKTOP);
        const desktopMarginStyleInfo = this.getMarginStyleInfo(rawStyleInfo, referenceNode);
        const desktopPaddingStyleInfo = this.getPaddingStyleInfo(rawStyleInfo, referenceNode);
        Object.assign(facts, { desktopMarginStyleInfo, desktopPaddingStyleInfo });
    }

    mergeSpacingInfo({ fact }) {
        if (fact === "desktopMarginStyleInfo") {
            // Prevent override of desktopMarginStyleInfo:
            // use case is top -> down traversal, margin info of the ancestor is
            // kept.
            return true;
        }
    }

    // TODO EGGMAIL NOW: generalize the content of this function, there are
    // multiple aspects to consider for the wrapping table:
    // - spacing
    // - horizontal centering (vertical centering does not happen on a spacing table, it should
    // happen more globally (and requires handling (TODO)))
    //
    buildMarginNode(facts) {
        // TODO EGGMAIL: discard negative paddings
        // for % values, use computed value in px (desktop mode) instead
        const marginNode = new SpacingNode();
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
        for (const side of DIRECTION_VARIANTS) {
            const value = styleInfo.getPropertyValue(`margin-${side}`);
            const { number, unit } = parseCssValue(value);
            if (number > 0 && unit === "px") {
                // The margin spacing node is meant as a wrapper and replaces
                // static margin by padding on the main wrapper cell.
                setAttributes({ style: { [`padding-${side}`]: value } }, "cell");
            }
        }
        if (isRelevant) {
            return marginNode;
        }
    }

    buildPaddingNode(facts) {
        const paddingNode = new SpacingNode();
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
            if (number > 0 && unit === "px") {
                setAttributes({ style: { [`padding-${side}`]: value } }, "cell");
            }
        }
        if (isRelevant) {
            return paddingNode;
        }
    }

    applyDefaultSpacing(layout, { emailNode }) {
        let contextNode;
        let currentNode = emailNode;
        do {
            contextNode = currentNode.lastReferenceNode;
            currentNode = currentNode.parent;
        } while (currentNode && !contextNode);
        if (!contextNode) {
            contextNode = this.config.referenceDocument.body;
        }
        if (!this.isBlock(contextNode)) {
            return;
        }
        const styleContext = { style: this.getContextStyleInfo(contextNode) };
        if (
            emailNode.analysis.facts.desktopMarginStyleInfo &&
            !paragraphRelatedElements.includes(layout.ancestorTag)
        ) {
            const marginNode = this.buildMarginNode(emailNode.analysis.facts);
            if (marginNode) {
                marginNode.layout.setAttributes(styleContext, "cell");
                emailNode.marginNode = marginNode;
            }
        }
        if (
            emailNode.analysis.facts.desktopPaddingStyleInfo &&
            !paragraphRelatedElements.includes(layout.descendantTag)
        ) {
            const paddingNode = this.buildPaddingNode(emailNode.analysis.facts);
            if (paddingNode) {
                paddingNode.layout.setAttributes(styleContext, "cell");
                emailNode.paddingNode = paddingNode;
            }
        }
    }

    cacheSpacingStyleInfo() {
        const treeWalker = this.createReferenceTreeWalker((node) =>
            node.nodeType === Node.ELEMENT_NODE
                ? NodeFilter.FILTER_ACCEPT
                : NodeFilter.FILTER_REJECT
        );
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

    provideStyleRules(rules) {
        // Allow paragraph-related elements to keep their top/bottom margins
        rules.allow(/^margin(-(top|bottom))?$/, {
            when: [
                ({ referenceNode }) => paragraphRelatedElements.includes(referenceNode.nodeName),
                ({ propertyName, propertyValue }) => {
                    if (propertyName === "margin" || propertyName === "padding") {
                        const values = this.decomposeSpacingShorthandValue(propertyValue);
                        return values.every((value) => {
                            const { number, unit } = parseCssValue(value);
                            return number !== undefined && (number === 0 || unit === "px");
                        });
                    } else {
                        const { number, unit } = parseCssValue(propertyValue);
                        return number === 0 || unit === "px";
                    }
                },
            ],
        });
    }
}

registry.category("mail-html-conversion-main-plugins").add(SpacingPlugin.id, SpacingPlugin);
