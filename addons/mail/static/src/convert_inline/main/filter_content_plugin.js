import { paragraphRelatedElements } from "@html_editor/utils/dom_info";
import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { Rules } from "../core/rules_models";
import { DIRECTION_VARIANTS } from "../core/utils";
import { withSequence } from "@html_editor/utils/resource";
import { DIMENSIONS } from "../hooks";

const BLOCKED_PSEUDO_CLASSES = new Set([
    "active",
    "focus",
    "focus-within",
    "hover",
    "link",
    "target",
    "visited",
]);
const INDIRECT_CSS_PROPERTY_VALUES = new Set([
    "inherit",
    "initial",
    "unset",
    "revert",
    "revert-layer",
]);
const ALLOWED_CSS_DISPLAY_VALUES = new Set(["block", "inline", "inline-block", "none"]);
const { DESKTOP, MOBILE } = DIMENSIONS;

export class FilterContentPlugin extends Plugin {
    static id = "filterContent";
    static dependencies = [
        "math",
        "measurementSnapshot",
        "responsiveBlock",
        "rules",
        "style",
        "referenceNode",
    ];
    static shared = ["getBodyGlobalStyleInfo", "getBodyTextStyleInfo", "isInvisible"];
    resources = {
        attribute_rules_processors: [
            [this.provideAttributeRules.bind(this), FilterContentPlugin.id],
        ],
        element_layout_analysis_processors: withSequence(1, this.analyzeElementLayout.bind(this)),
        style_rules_processors: [[this.provideStyleRules.bind(this), FilterContentPlugin.id]],
        is_blocked_rule_selector_predicates: this.blockUserContextSelectors.bind(this),
        should_discard_reference_node_predicates: this.isInvisible.bind(this),
    };

    setup() {
        this.bodyTextStyleRules = new Rules();
        this.bodyGlobalStyleRules = new Rules();
        this.provideBodyStyleRules();
    }

    analyzeElementLayout({ analysis }, { referenceNode, parentEmailNode }) {
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
            return;
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
    }

    provideBodyStyleRules() {
        const textRules = this.bodyTextStyleRules.forPlugin(FilterContentPlugin.id);
        textRules.allow("font-size");
        textRules.allow("font-weight");
        textRules.allow("line-height");
        const globalRules = this.bodyGlobalStyleRules.forPlugin(FilterContentPlugin.id);
        globalRules.allow("direction");
    }

    /**
     * Return a copy of the body styleInfo filtered with its own rules for
     * text ancestors (eg presentation table td)
     */
    getBodyTextStyleInfo() {
        return this.filterStyleInfo(
            this.getRawStyleInfo(this.config.referenceDocument.body),
            this.config.referenceDocument.body,
            this.bodyTextStyleRules
        );
    }

    /**
     * Return a copy of the body styleInfo filtered with its own rules for
     * main layout ancestors (eg main table)
     */
    getBodyGlobalStyleInfo() {
        return this.filterStyleInfo(
            this.getRawStyleInfo(this.config.referenceDocument.body),
            this.config.referenceDocument.body,
            this.bodyGlobalStyleRules
        );
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
    }

    provideStyleRules(rules) {
        this.genericMiscStyleRules(rules);
        this.genericTextAndFontStyleRules(rules);
        this.genericBackgroundStyleRules(rules);
        this.genericSpacingStyleRules(rules);
        this.genericLayoutStyleRules(rules);
        this.genericTableStyleRules(rules);
    }

    genericMiscStyleRules(rules) {
        rules.block(/.*/, {
            // Block all style for `t` elements
            // TODO EGGMAIL: should we wrap the `T` element to a `DIV` or a `SPAN`?
            // should we move the style there?
            when: ({ referenceNode }) => referenceNode.nodeName === "T",
        });
        rules.block(/.*/, {
            when: ({ propertyValue }) => INDIRECT_CSS_PROPERTY_VALUES.has(propertyValue),
        });
        rules.allow("overflow");
        rules.allow("opacity");
        rules.allow("direction");
    }

    genericTextAndFontStyleRules(rules) {
        // TODO EGGMAIL: replace regexes by exhaustive string lists? (rules optimization)
        // Avoid text-shadow (poor support)
        // text-decoration is safe but limited (underline mostly)
        rules.allow(/^font(-.*)?$/);
        rules.allow(/^text-(align|decoration|transform|indent)$/);
        rules.allow("line-height");
        rules.allow("letter-spacing");
        rules.allow("word-spacing");
        rules.allow("white-space");
        rules.allow("color");
    }

    genericBackgroundStyleRules(rules) {
        // TODO EGGMAIL: maybe not restrictive enough
        rules.allow(/^background(-.*)?$/);
    }

    genericSpacingStyleRules(rules) {
        // TODO EGGMAIL: maybe not restrictive enough (margin not well supported)
        // check if spacing should be handled by geometry only
        // consider box-sizing for paddings&margins -> use values from band/cluster computations
        rules.allow(/^padding(-.*)?$/);
        rules.allow(/^margin(-.*)?$/, {
            when: [
                ({ referenceNode }) => paragraphRelatedElements.includes(referenceNode.nodeName),
                ({ attributeValue }) => attributeValue !== "auto",
            ],
        });
        rules.allow(/^border(-.*)?$/);
        rules.allow(/^border-(collapse|spacing)$/);
        // TODO EGGMAIL: some strategies require that children don't keep their
        // width/height as specified -> investigate how to handle that (hybrid fluid)
        // rules.allow(/^(width|height)$/);
        // rules.allow(/^(max|min)-(width|height)$/);
    }

    genericLayoutStyleRules(rules) {
        rules.allow("display", {
            when: ({ propertyValue }) => ALLOWED_CSS_DISPLAY_VALUES.has(propertyValue),
        });
        rules.allow("vertical-align");
    }

    genericTableStyleRules(rules) {
        rules.allow("table-layout");
        rules.allow("border-collapse");
        rules.allow("border-spacing");
        rules.allow("empty-cells");
    }

    genericListStyleRules(rules) {
        rules.allow(/^list-style(-.*)?$/);
    }

    hasVisibleBorder(element, layoutDimensions) {
        const computedStyle = this.getComputedStyle(element, layoutDimensions);
        return DIRECTION_VARIANTS.some((side) => {
            const width = parseFloat(computedStyle.getPropertyValue(`border-${side}-width`));
            const borderStyle = computedStyle.getPropertyValue(`border-${side}-style`);
            return width > 0 && borderStyle !== "none" && borderStyle !== "hidden";
        });
    }

    isInvisible(referenceNode) {
        if (!referenceNode) {
            return true;
        }
        let { rect } = this.getLayoutBlock(referenceNode) ?? {};
        if (!rect) {
            rect = this.getBoundingClientRect(referenceNode);
        }
        // TODO EGGMAIL: investigate if some more node should bypass this rule
        if (
            rect &&
            rect.height === 0 &&
            (referenceNode.nodeType !== Node.ELEMENT_NODE || !this.hasVisibleBorder(referenceNode))
        ) {
            return true;
        }
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(FilterContentPlugin.id, FilterContentPlugin);
