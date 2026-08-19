import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { DIMENSIONS } from "../hooks";
import { isTableCell } from "@html_editor/utils/dom_info";
import {
    ALLOWED_CSS_DISPLAY_VALUES,
    BLOCKED_CSS_POSITION_VALUES,
    BLOCKED_PSEUDO_CLASSES,
    INDIRECT_CSS_PROPERTY_VALUES,
} from "../core/utils";

// TODO EGGMAIL: investigate if some more node should bypass the invisible rule
const ALLOWED_IF_INVISIBLE_ELEMENT = new Set(["BR", "T"]);
const { DESKTOP, MOBILE } = DIMENSIONS;

export class FilterContentPlugin extends Plugin {
    static id = "filterContent";
    static dependencies = [
        "border",
        "math",
        "measurementSnapshot",
        "responsiveBlock",
        "rules",
        "spacing",
        "style",
        "referenceNode",
    ];
    static shared = ["isInvisible"];
    resources = {
        attribute_rules_processors: [
            [this.provideAttributeRules.bind(this), FilterContentPlugin.id],
        ],
        element_layout_analysis_processors: [
            withSequence(1, this.analyzeParentMergeability.bind(this)),
        ],
        style_rules_processors: [[this.provideStyleRules.bind(this), FilterContentPlugin.id]],
        is_blocked_rule_selector_predicates: this.blockUserContextSelectors.bind(this),
        should_discard_reference_node_predicates: [
            this.isInvisible.bind(this),
            this.isPositionAbsolute.bind(this),
        ],
        reference_node_tag_name_processors: this.defineEffectiveTagName.bind(this),
    };

    analyzeParentMergeability(defaultEmailNodeArguments, { referenceNode, parentEmailNode }) {
        const { analysis } = defaultEmailNodeArguments;
        const node = referenceNode;
        let parentNode;
        if (
            !parentEmailNode ||
            parentEmailNode.referenceNodes.length === 0 ||
            !this.isBlock(node) ||
            // TODO EGGMAIL: arbitrary choice to take the lastReferenceNode to motivate
            !this.isBlock((parentNode = parentEmailNode.lastReferenceNode)) ||
            // TODO EGGMAIL: make a mergeable nodes names resource
            (parentNode.nodeName !== "DIV" && parentNode.nodeName !== "SECTION")
        ) {
            analysis.parsingFacts.canParentMerge = false;
            return defaultEmailNodeArguments;
        }
        const mobileParentBlock = this.getLayoutBlock(parentNode, MOBILE);
        const mobileBlock = this.getLayoutBlock(node, MOBILE);
        const desktopParentBlock = this.getLayoutBlock(parentNode, DESKTOP);
        const desktopBlock = this.getLayoutBlock(node, DESKTOP);
        if (
            !this.areRectEqual(mobileParentBlock.rect, mobileBlock.rect) ||
            !this.areRectEqual(desktopParentBlock.rect, desktopBlock.rect)
        ) {
            analysis.parsingFacts.canParentMerge = false;
        }
        return defaultEmailNodeArguments;
    }

    defineEffectiveTagName(tagName) {
        // TODO EGGMAIL: apply a stricter conversion:
        // keep an allowed block tagNames list (eg, table, tr, td, ...)
        // and convert anything that is not in that table into "DIV"
        if (tagName === "SECTION") {
            return "DIV";
        }
        return tagName;
    }

    blockUserContextSelectors(complexSelector) {
        if (
            complexSelector.simpleSelectorList.some(
                (simpleSelector) =>
                    simpleSelector.prefix === "::" || // Block pseudo-element
                    (simpleSelector.prefix === ":" && // Block user-context-related pseudo-class
                        BLOCKED_PSEUDO_CLASSES.has(simpleSelector.content))
            )
        ) {
            return true;
        }
    }

    // TODO EGGMAIL: evaluate if some classes/data-attributes are used in python
    // and should be allowed. Use a "fix" rule to allow some classes/data-attributes
    /**
     * Remove irrelevant attributes from the sent email to minimize size
     */
    provideAttributeRules(rules) {
        // TODO EGGMAIL: exception for mail-quote data-attributes, and maybe classes
        // use a fix rule in this case
        rules.block(/data-.+/);
        // TODO EGGMAIL: verify that `t` elements don't need classes in some edge cases
        rules.block("class");
        // Inline style must be computed by a strategy Plugin using StyleInfo
        rules.block("style");
        rules.block(/.*/, {
            // TODO EGGMAIL: should we allow attributes not starting with `t-` for qweb `t` elements?
            when: ({ attributeName, referenceNode }) =>
                referenceNode.nodeName === "T" && !attributeName.startsWith("t-"),
        });
        rules.block("srcset");
    }

    provideStyleRules(rules) {
        this.genericMiscStyleRules(rules);
        this.genericTextAndFontStyleRules(rules);
        this.genericBackgroundStyleRules(rules);
        this.genericLayoutStyleRules(rules);
        this.genericTableStyleRules(rules);
    }

    genericMiscStyleRules(rules) {
        rules.block(/.*/, {
            // Block all style for `t` elements
            // TODO EGGMAIL: should we wrap the `T` element to a `DIV` or a `SPAN`?
            // should we move the style there?
            when: ({ referenceNode }) =>
                referenceNode.nodeName === "T" || referenceNode.nodeName === "BR",
        });
        rules.block(/.*/, {
            // TODO EGGMAIL: controversial rule, but cases where removing an
            // indirect css property value cause a style issue should be
            // enforced with a "fix" rule which will compute a resolved style
            // value. This can not be done in a generic way as some computed
            // values are not what is actually required in the email (eg width:
            // 100% being computed as width 737.21px).
            when: ({ propertyValue }) => INDIRECT_CSS_PROPERTY_VALUES.has(propertyValue),
        });
        rules.allow("overflow");
        rules.allow("opacity");
        rules.allow("direction");
    }

    genericTextAndFontStyleRules(rules) {
        // TODO EGGMAIL: replace regexes by exhaustive string lists? (rules optimization)
        // Avoid text-shadow (poor support)
        rules.allow(/^font(-.*)?$/);
        // text-decoration is safe but limited (underline mostly)
        // TODO EGGMAIL: text-align values should be fixed to not include "start" or "end" (converted with rtl to left or right)
        rules.allow(/^text-(align|decoration|transform|indent)$/);
        // text-decoration-line has very low support => fallback to text-decoration
        rules.fix("text-decoration-line", {
            how: ({ propertyValue }) => {
                if (propertyValue === "underline") {
                    return { propertyName: "text-decoration", propertyValue };
                }
            },
        });
        rules.allow("line-height");
        rules.allow("letter-spacing");
        rules.allow("word-spacing");
        rules.allow("white-space");
        rules.allow("color");
    }

    genericBackgroundStyleRules(rules) {
        // TODO EGGMAIL: maybe not restrictive enough
        rules.allow("background");
        rules.allow("background-color");
    }

    genericLayoutStyleRules(rules) {
        rules.allow("display", {
            when: ({ propertyValue }) => ALLOWED_CSS_DISPLAY_VALUES.has(propertyValue),
        });
        rules.allow("vertical-align");
        rules.fix("vertical-align", {
            when: ({ propertyValue }) => INDIRECT_CSS_PROPERTY_VALUES.has(propertyValue),
            how: ({ referenceNode }) => this.getStylePropertyValue(referenceNode, "vertical-align"),
        });
    }

    genericTableStyleRules(rules) {
        const isTable = ({ referenceNode }) => referenceNode.nodeName === "TABLE";
        rules.allow("table-layout", { when: isTable });
        rules.allow("empty-cells", { when: isTable });
        rules.allow("width", { when: isTable });
        rules.require("width", { when: isTable, how: () => ({ propertyValue: "100%" }) });
        rules.require("max-width", {
            when: [isTable, ({ propertyValue }) => propertyValue !== "100%"],
            how: () => ({ propertyValue: "100%" }),
        });
        rules.allow("height", { when: ({ referenceNode }) => referenceNode.nodeName === "TR" });
        rules.allow("width", {
            when: ({ referenceNode }) => isTableCell(referenceNode.nodeName),
        });
        rules.allow("background-color", {
            when: ({ referenceNode }) => referenceNode.nodeName === "TH",
        });
        rules.require("line-height", {
            when: ({ referenceNode }) => isTableCell(referenceNode),
            how: () => ({ propertyValue: "1.2" }), // typical "normal" value
        });
    }

    genericListStyleRules(rules) {
        rules.allow(/^list-style(-.*)?$/);
    }

    isInvisible(referenceNode) {
        if (!referenceNode) {
            return true;
        }
        let { rect } = this.getLayoutBlock(referenceNode) ?? {};
        if (!rect) {
            rect = this.getBoundingClientRect(referenceNode);
        }
        const isBlock = this.isBlock(referenceNode);
        if (
            !ALLOWED_IF_INVISIBLE_ELEMENT.has(referenceNode.nodeName) &&
            rect &&
            rect[isBlock ? "height" : "width"] === 0 &&
            (referenceNode.nodeType !== Node.ELEMENT_NODE || !this.hasVisibleBorder(referenceNode))
        ) {
            return true;
        }
    }

    isPositionAbsolute(referenceNode) {
        if (referenceNode.nodeType !== Node.ELEMENT_NODE) {
            return;
        }
        if (
            BLOCKED_CSS_POSITION_VALUES.has(this.getStylePropertyValue(referenceNode, "position"))
        ) {
            return true;
        }
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(FilterContentPlugin.id, FilterContentPlugin);
