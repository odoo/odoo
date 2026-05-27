import { paragraphRelatedElements } from "@html_editor/utils/dom_info";
import { DIMENSIONS } from "../hooks";
import { Plugin } from "../plugin";
import { ElementLayout } from "../core/render_models";
import { StyleInfo } from "../core/style_models";
import { Rules } from "../core/rules_models";
import { registry } from "@web/core/registry";
import { parseCssValue } from "../css_parsers";
import { SpacingNode } from "./spacing_models";

const { DESKTOP, MOBILE } = DIMENSIONS;
const MARGINS = ["margin-top", "margin-right", "margin-bottom", "margin-left"];
const PADDINGS = ["padding-top", "padding-right", "padding-bottom", "padding-left"];

/**
 * TODO EGGMAIL: handle vertical alignment? (should be done at a higher level),
 * eg vertical alignment necessary because a horizontal cell is bigger than
 * another.
 * TODO EGGMAIL: handle display-flex alignments as well? They don't use margin
 * but need centering => to investigate.
 */
export class SpacingPlugin extends Plugin {
    static id = "spacing";
    static dependencies = ["contextStyle", "referenceNode", "responsiveBlock", "rules", "style"];
    resources = {
        on_parse_layout_with_dimensions_handlers: this.cacheSpacingStyleInfo.bind(this),
        reference_node_facts_processors: this.addSpacingFacts.bind(this),
        refine_layout_processors: this.applyDefaultSpacing.bind(this),
        style_rules_processors: [[this.provideStyleRules.bind(this), SpacingPlugin.id]],
    };

    setup() {
        this.spacingStyleRules = new Rules();
        this.provideSpacingStyleRules();
    }

    addSpacingFacts(facts, { referenceNode }) {
        Object.assign(facts, {
            desktopSpacingStyleInfo: this.getSpacingStyleInfo(referenceNode, DESKTOP),
            desktopBlock: this.getLayoutBlock(referenceNode, DESKTOP),
            mobileSpacingStyleInfo: this.getSpacingStyleInfo(referenceNode, MOBILE),
            mobileBlock: this.getLayoutBlock(referenceNode, MOBILE),
        });
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
        const styleInfo = facts.desktopSpacingStyleInfo;
        let isRelevant = false;
        const setAttributes = (options) => {
            marginLayout.setAttributes(options);
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
        for (const margin of MARGINS) {
            const value = styleInfo.getPropertyValue(margin);
            const { number, unit } = parseCssValue(value);
            if (number > 0 && unit === "px") {
                setAttributes({ style: { [margin]: value } }, "cell");
            }
        }
        if (isRelevant) {
            return marginNode;
        }
    }

    buildPaddingNode(facts) {
        const paddingNode = new SpacingNode();
        const paddingLayout = paddingNode.layout;
        const styleInfo = facts.desktopSpacingStyleInfo;
        let isRelevant = false;
        const setAttributes = (options) => {
            paddingLayout.setAttributes(options);
            isRelevant = true;
        };
        for (const padding of PADDINGS) {
            const value = styleInfo.getPropertyValue(padding);
            const { number, unit } = parseCssValue(value);
            if (number > 0 && unit === "px") {
                setAttributes({ style: { [padding]: value } }, "cell");
            }
        }
        if (isRelevant) {
            return paddingNode;
        }
    }

    applyDefaultSpacing(layout, { emailNode }) {
        if (
            layout.constructor !== ElementLayout ||
            !emailNode.analysis.facts.desktopBlock ||
            paragraphRelatedElements.includes(layout.tag)
        ) {
            return;
        }
        // TODO EGGMAIL: arbitrary fallback on body, maybe recursive search on parent is more
        // appropriate?
        const contextNode = emailNode.lastReferenceNode ?? this.config.referenceDocument.body;
        const styleContext = {
            style: this.getContextStyleInfo(contextNode),
        };
        const marginNode = this.buildMarginNode(emailNode.analysis.facts);
        if (marginNode) {
            marginNode.layout.setAttributes(styleContext, "cell");
            emailNode.marginNode = marginNode;
        }
        const paddingNode = this.buildPaddingNode(emailNode.analysis.facts);
        if (paddingNode) {
            paddingNode.layout.setAttributes(styleContext, "cell");
            emailNode.paddingNode = paddingNode;
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

    /**
     * Returns a normalized spacing styleInfo containing only longhand css
     * properties. Only support simple padding/margin variants.
     * @see spacingStyleRules
     *
     * @returns {StyleInfo}
     */
    getSpacingStyleInfo(referenceNode, layoutDimensions = undefined) {
        const rawSpacingStyleInfo = this.filterStyleInfo(
            this.getRawStyleInfo(referenceNode, layoutDimensions),
            referenceNode,
            this.spacingStyleRules
        );
        // TODO EGGMAIL: this is incomplete CSS value parsing, would be unnecessary
        // if we have a complete value parser.
        const longhandStyleInfo = new StyleInfo();
        const shorthandStyleInfo = new StyleInfo();
        const suffixes = ["top", "right", "bottom", "left"];
        const setShorthandPropertyValues = (propertyName, values, priority, sequence) => {
            suffixes.forEach((suffix, index) => {
                const name = `${propertyName}-${suffix}`;
                shorthandStyleInfo.setProperty(name, values[index], priority, sequence);
            });
        };
        for (const [
            propertyName,
            { value, priority, sequence },
        ] of rawSpacingStyleInfo.getSortedEntries()) {
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
        const spacingRules = this.spacingStyleRules.forPlugin(SpacingPlugin.id);
        // TODO EGGMAIL: support more spacing cases?
        spacingRules.allow(/^padding(-(top|right|bottom|left))?$/);
        spacingRules.allow(/^margin(-(top|right|bottom|left))?$/);
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
