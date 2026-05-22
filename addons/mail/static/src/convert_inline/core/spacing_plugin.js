import { paragraphRelatedElements } from "@html_editor/utils/dom_info";
import { DIMENSIONS } from "../hooks";
import { Plugin } from "../plugin";
import { ElementLayout } from "./render_models";
import { StyleInfo } from "./style_models";
import { Rules } from "./rules_models";
import { registry } from "@web/core/registry";
import { parseCssValue } from "../css_parsers";

const { DESKTOP, MOBILE } = DIMENSIONS;

export class SpacingPlugin extends Plugin {
    static id = "spacing";
    static dependencies = ["referenceNode", "responsiveBlock", "style"];
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

    applyDefaultSpacing(layout, { emailNode }) {
        if (
            layout.constructor !== ElementLayout ||
            !emailNode.analysis.facts.desktopBlock ||
            paragraphRelatedElements.includes(layout.tag)
        ) {
            return;
        }
        // how to apply the related table the best way on the layout?
        // include a container slot and a childContainer slot in LayoutModel, so that we can
        // still access the main info easily, but we also have easy access to padding/margin structures?

        // padding handling

        // margin handling
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
