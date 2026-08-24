import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { StyleInfo } from "./style_models";
import { Rules } from "./rules_models";

export class RulesPlugin extends Plugin {
    static id = "rules";
    static dependencies = ["measurementSnapshot", "style"];
    static shared = [
        "applyAttributeRules",
        "applyStyleRules",
        "cloneReferenceNode",
        "filterAttributes",
        "filterStyleInfo",
        "getAttributes",
        "getStyleInfo",
    ];
    resources = {
        on_layout_dimensions_updated_handlers: this.onLayoutDimensionsUpdated.bind(this),
        on_will_start_conversion_handlers: this.specifyRules.bind(this),
    };

    setup() {
        this.nodeToStyleInfos = new WeakMap();
    }

    specifyRules() {
        this.attributeRules = this.processRules(
            "attribute_rules_processors",
            new Rules({ defaultAllowed: true })
        );
        this.styleRules = this.processRules("style_rules_processors", new Rules());
    }

    cloneReferenceNode(referenceNode, layoutDimensions = this.layoutDimensions) {
        let clone;
        if (referenceNode.nodeType === Node.ELEMENT_NODE) {
            clone = this.config.referenceDocument.createElement(referenceNode.tagName);
            this.applyAttributeRules(clone, this.getAttributes(referenceNode));
            this.applyStyleRules(clone, this.getStyleInfo(referenceNode, layoutDimensions));
        } else {
            clone = referenceNode.cloneNode();
        }
        return clone;
    }

    getStyleInfoToFiltered(referenceNode) {
        if (!this.nodeToStyleInfos.has(referenceNode)) {
            this.nodeToStyleInfos.set(referenceNode, new WeakMap());
        }
        return this.nodeToStyleInfos.get(referenceNode);
    }

    applyAttributeRules(targetElement, attributes) {
        if (!targetElement || targetElement.nodeType !== Node.ELEMENT_NODE) {
            return targetElement;
        }
        for (const attributeName of targetElement.getAttributeNames()) {
            targetElement.removeAttribute(attributeName);
        }
        for (const [attributeName, attributeValue] of Object.entries(attributes)) {
            targetElement.setAttribute(attributeName, attributeValue);
        }
        return targetElement;
    }

    // TODO EGGMAIL: allow providing callbacks to do extra processing during
    // processData
    filterAttributes(attributes, referenceNode, rules = this.attributeRules) {
        if (typeof referenceNode === "string") {
            referenceNode = this.config.referenceDocument.createElement(referenceNode);
        }
        let attributesMap = attributes;
        if (Array.isArray(attributes)) {
            attributesMap = new Map(attributes);
        } else if (!(attributes instanceof Map)) {
            attributesMap = new Map(Object.entries(attributes));
        }
        if (!rules) {
            return Object.fromEntries(attributesMap);
        }
        const filteredAttributes = {};
        rules.processData(attributesMap, {
            getRuleArgs: (attributeName, attributeValue) => [
                {
                    attributeName,
                    attributeValue,
                    referenceNode,
                },
            ],
            onPass: (attributeName, attributeValue, fixedArgs = {}) => {
                const name = fixedArgs.attributeName ?? attributeName;
                const value = fixedArgs.attributeValue ?? attributeValue;
                if (value !== undefined) {
                    filteredAttributes[name] = value;
                }
            },
            onFail: (attributeName) => {
                delete filteredAttributes[attributeName];
            },
            onMiss: (attributeName) => {
                console.warn(
                    `Attribute ${attributeName} is missing or was marked as blocked on the given attributes, in relation to referenceNode`,
                    attributes,
                    referenceNode
                );
            },
        });
        return filteredAttributes;
    }

    getAttributes(referenceNode) {
        return this.filterAttributes(
            referenceNode
                .getAttributeNames()
                .map((name) => [name, referenceNode.getAttribute(name)]),
            referenceNode
        );
    }

    applyStyleRules(targetElement, styleInfo) {
        if (!targetElement || targetElement.nodeType !== Node.ELEMENT_NODE) {
            return targetElement;
        }
        targetElement.removeAttribute("style");
        styleInfo.applyOnElement(targetElement);
        return targetElement;
    }

    /**
     * Return a new styleInfo instance filtered with rules
     */
    // TODO EGGMAIL: allow providing callbacks to do extra processing during
    // processData -> this would be necessary for eg image_strategy_plugin neutralization
    // => then, we could use border_plugin neutralizeBorders with callbacks
    // => then, no need to manually remove keys from a styleInfo to copy
    // them on another styleInfo, we can directly filter the styleInfo + extra processing
    filterStyleInfo(styleInfo, referenceNode, rules = this.styleRules) {
        if (typeof referenceNode === "string") {
            referenceNode = this.config.referenceDocument.createElement(referenceNode);
        }
        const filteredStyleInfo = new StyleInfo();
        if (!rules) {
            return filteredStyleInfo.merge(styleInfo);
        }
        const shouldCache =
            this.config.reference.contains(referenceNode) && rules === this.styleRules;
        if (shouldCache) {
            const styleInfoToFiltered = this.getStyleInfoToFiltered(referenceNode);
            if (styleInfoToFiltered.has(styleInfo)) {
                return filteredStyleInfo.merge(styleInfoToFiltered.get(styleInfo));
            }
        }
        rules.processData(styleInfo, {
            getRuleArgs: (propertyName, propertyInfo) => [
                {
                    propertyName,
                    propertyValue: propertyInfo?.value,
                    propertyPriority: propertyInfo?.priority ?? "",
                    referenceNode,
                },
            ],
            onPass: (propertyName, propertyInfo, fixedArgs = {}) => {
                const name = fixedArgs.propertyName ?? propertyName;
                const value = fixedArgs.propertyValue ?? propertyInfo?.value;
                const priority = fixedArgs.propertyPriority ?? propertyInfo?.priority ?? "";
                const sequence = fixedArgs.propertySequence ?? propertyInfo?.sequence ?? 0;
                if (value !== undefined) {
                    filteredStyleInfo.setProperty(name, value, priority, sequence);
                }
            },
            onMiss: (propertyName) => {
                // TODO EGGMAIL: special values like unset, inherit, ... must
                // be handled (either computed style or search parents), need to
                // check units and other values too
                // TODO EGGMAIL: search parents before applying computed style?
                filteredStyleInfo.setProperty(
                    propertyName,
                    this.getStylePropertyValue(referenceNode)
                );
            },
        });
        if (shouldCache) {
            const styleInfoToFiltered = this.getStyleInfoToFiltered(referenceNode);
            styleInfoToFiltered.set(styleInfo, new StyleInfo().merge(filteredStyleInfo));
        }
        return filteredStyleInfo;
    }

    getStyleInfo(referenceNode, layoutDimensions = this.layoutDimensions) {
        return this.filterStyleInfo(
            this.getRawStyleInfo(referenceNode, layoutDimensions),
            referenceNode
        );
    }

    onLayoutDimensionsUpdated(layoutDimensions) {
        this.layoutDimensions = layoutDimensions;
    }
}

registry.category("mail-html-conversion-core-plugins").add(RulesPlugin.id, RulesPlugin);
