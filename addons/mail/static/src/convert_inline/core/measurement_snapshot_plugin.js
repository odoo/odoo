import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import {
    generateLonghands,
    BACKGROUND_VARIANTS,
    CONTOUR_VARIANTS,
    DIRECTION_VARIANTS,
    DOM_RECT_PROPERTIES,
    FONT_VARIANTS,
} from "@mail/convert_inline/core/utils";
import { ComputedStyle } from "./style_models";
import { blockTagNames } from "@html_editor/utils/blocks";

export class MeasurementSnapshotPlugin extends Plugin {
    static id = "measurementSnapshot";
    static dependencies = ["responsive"];
    static shared = [
        "getBoundingClientRect",
        "getComputedStyle",
        "getNodeClusterRange",
        "getRectValue",
        "getStylePropertyValue",
        "isBlock",
        "registerStyleProperty",
    ];

    resources = {
        // Typical shorthands for emails.
        // They are recorded by default in a getComputedStyle snapshot.
        // Usage of longhand properties is recommended.
        default_shorthand_to_longhand_properties: {
            background: new Set(generateLonghands("background", [BACKGROUND_VARIANTS])),
            border: new Set(generateLonghands("border", [DIRECTION_VARIANTS, CONTOUR_VARIANTS])),
            font: new Set(generateLonghands("font", [FONT_VARIANTS])),
            margin: new Set(generateLonghands("margin", [DIRECTION_VARIANTS])),
            outline: new Set(generateLonghands("outline", [CONTOUR_VARIANTS])),
            padding: new Set(generateLonghands("padding", [DIRECTION_VARIANTS])),
        },
        // Properties recorded by default in a getComputedStyle snapshot.
        default_computed_properties: [
            "border-collapse",
            "box-sizing",
            "color",
            "display",
            "height",
            "line-height",
            "max-height",
            "max-width",
            "min-height",
            "min-width",
            "position",
            "text-decoration",
            "text-transform",
            "text-align",
            "vertical-align",
            "width",
        ],
        on_layout_dimensions_updated_handlers: this.onLayoutDimensionsUpdated.bind(this),
        on_will_load_reference_content_handlers: () => this.config.updateLayoutDimensions(),
    };

    setup() {
        this.styleProperties = new Set(); // properties to register in a snapshot
        this.layoutToComputedStyle = new Map(); // dimensions to WeakMap of element to computed snapshot proxy
        this.domRectProperties = new Set(DOM_RECT_PROPERTIES); // properties of a DOMRect
        this.layoutToBoundingClientRect = new Map(); // dimensions to WeakMap of element/range to bounding client rect snapshot proxy
        this.nodeToClusterRange = new WeakMap(); // startNode to endNode->range Map
        this.setupProperties();
    }

    setupShorthandToLonghand() {
        this.shorthandToLonghand = this.getResource(
            "default_shorthand_to_longhand_properties"
        ).reduce((shortHandToLonghand, current) => {
            for (const property in current) {
                shortHandToLonghand[property] = current[property].union(
                    shortHandToLonghand[property] ?? new Set()
                );
            }
            return shortHandToLonghand;
        }, {});
    }

    setupProperties() {
        this.setupShorthandToLonghand();
        for (const propertyName in this.shorthandToLonghand) {
            this.registerStyleProperty(propertyName);
        }
        const longhandProperties = this.getResource("default_computed_properties");
        for (const propertyName of longhandProperties) {
            this.registerStyleProperty(propertyName);
        }
    }

    onLayoutDimensionsUpdated(layoutDimensions) {
        this.layoutDimensions = layoutDimensions;
    }

    getNodeToBoundingClientRect(layoutDimensions) {
        if (!layoutDimensions) {
            layoutDimensions = this.layoutDimensions;
        }
        if (!this.layoutToBoundingClientRect.has(layoutDimensions)) {
            this.layoutToBoundingClientRect.set(layoutDimensions, new WeakMap());
        }
        return this.layoutToBoundingClientRect.get(layoutDimensions);
    }

    getNodeToComputedStyle(layoutDimensions) {
        if (!layoutDimensions) {
            layoutDimensions = this.layoutDimensions;
        }
        if (!this.layoutToComputedStyle.has(layoutDimensions)) {
            this.layoutToComputedStyle.set(layoutDimensions, new WeakMap());
        }
        return this.layoutToComputedStyle.get(layoutDimensions);
    }

    cachedComputedStyleProxyHandler(element, pseudoElt = null) {
        const layoutDimensions = this.layoutDimensions;
        return {
            set: () => false,
            deleteProperty: () => false,
            get: (target, key, receiver) => {
                if (typeof key === "string" && !(key in target)) {
                    if (this.layoutDimensions !== layoutDimensions) {
                        // Force a re-compute (+ cache miss) for the missing key.
                        return this.getComputedStyle(
                            element,
                            pseudoElt,
                            layoutDimensions
                        ).getPropertyValue(key);
                    }
                    this.registerStyleProperty(key);
                    this.getStyleSnapshot(element, pseudoElt, target);
                }
                return Reflect.get(target, key, receiver);
            },
        };
    }

    registerStyleProperty(propertyName) {
        if (propertyName in this.shorthandToLonghand) {
            const propertyNames = this.shorthandToLonghand[propertyName];
            for (const longHandProperty of propertyNames) {
                this.registerStyleProperty(longHandProperty);
            }
        }
        if (!this.styleProperties.has(propertyName)) {
            this.styleProperties.add(propertyName);
        }
    }

    /**
     * ownerDocument can't always be used because a reference node may
     * have been adopted into the referenceDocument, and some browsers
     * don't update the `ownerDocument` property in that case.
     * This function should prioritize getting the referenceDocument
     * if possible/relevant.
     */
    getRelatedDocument(node) {
        const relatedDocument = this.config.referenceDocument.contains(node)
            ? this.config.referenceDocument
            : node.ownerDocument;
        return relatedDocument;
    }

    getStyleSnapshot(element, pseudoElt = null, styleSnapshot = {}) {
        const relatedDocument = this.getRelatedDocument(element);
        const computedStyle = relatedDocument.defaultView.getComputedStyle(element, pseudoElt);
        for (const propertyName of this.styleProperties) {
            if (!(propertyName in styleSnapshot)) {
                styleSnapshot[propertyName] = computedStyle.getPropertyValue(propertyName);
            }
        }
        return styleSnapshot;
    }

    /**
     * @param {HTMLElement|Range} cluster
     * @param {Object} rectSnapshot
     * @returns {DOMRect}
     */
    getBoundingClientRectSnapshot(cluster, rectSnapshot = {}) {
        const boundingClientRect = cluster.getBoundingClientRect();
        for (const propertyName of this.domRectProperties) {
            if (!(propertyName in rectSnapshot)) {
                rectSnapshot[propertyName] = boundingClientRect[propertyName];
            }
        }
        return rectSnapshot;
    }

    getNodeClusterRange(startNode, endNode = startNode) {
        const relatedDocument = this.getRelatedDocument(startNode);
        let range, nodeToClusterRange;
        const isInReference =
            this.config.referenceDocument.contains(startNode) &&
            this.config.referenceDocument.contains(endNode);
        if (isInReference) {
            nodeToClusterRange = this.nodeToClusterRange.get(startNode);
            range = nodeToClusterRange?.get(endNode);
        }
        if (!range) {
            range = relatedDocument.createRange();
            range.setStartBefore(startNode);
            range.setEndAfter(endNode);
        }
        if (isInReference) {
            if (!nodeToClusterRange) {
                nodeToClusterRange = new WeakMap();
                this.nodeToClusterRange.set(startNode, nodeToClusterRange);
            }
            nodeToClusterRange.set(endNode, range);
        }
        return range;
    }

    hasNodeComputedStyle(nodeToComputedStyle, element, pseudoElt = null) {
        if (!nodeToComputedStyle.has(element)) {
            return false;
        }
        const computedStyleMap = nodeToComputedStyle.get(element);
        return computedStyleMap.has(pseudoElt);
    }

    getNodeComputedStyle(nodeToComputedStyle, element, pseudoElt = null) {
        if (!nodeToComputedStyle.has(element)) {
            nodeToComputedStyle.set(element, new Map());
        }
        const computedStyleMap = nodeToComputedStyle.get(element);
        if (!computedStyleMap.has(pseudoElt)) {
            computedStyleMap.set(pseudoElt, this.getComputedStyleProxy(element, pseudoElt));
        }
        return computedStyleMap.get(pseudoElt);
    }

    getComputedStyleProxy(element, pseudoElt = null) {
        return new Proxy({}, this.cachedComputedStyleProxyHandler(element, pseudoElt));
    }

    computeStyleProxy(element, pseudoElt = null) {
        return this.getNodeComputedStyle(this.getNodeToComputedStyle(), element, pseudoElt);
    }

    /**
     * Returns a cached view of `getComputedStyle`. The cache is long-lived if the element is in
     * the reference HTML (associated with a given dimensionsKey), because the reference dimensions
     * are fixed relative to that dimensionsKey, and the cache can be reused if
     * this function is called on the same element.
     * The cache is short-lived otherwise (it has its own scope), and a new call to this function
     * will essentially generate a call to `getComputedStyle`.
     *
     * @param {HTMLElement} element
     * @returns {ComputedStyle} cached style
     */
    getComputedStyle(element, pseudoElt = null, layoutDimensions = this.layoutDimensions) {
        if (!this.config.referenceDocument.contains(element)) {
            // Only the style of an element inside the referenceDocument can be cached, as
            // the HTML and CSS content inside that document are fixed during conversion.
            return new ComputedStyle(this.getComputedStyleProxy(element, pseudoElt));
        }
        const nodeToComputedStyle = this.getNodeToComputedStyle(layoutDimensions);
        let computedStyleProxy;
        if (this.hasNodeComputedStyle(nodeToComputedStyle, element, pseudoElt)) {
            computedStyleProxy = nodeToComputedStyle.get(element);
        } else if (layoutDimensions !== this.layoutDimensions) {
            console.warn(
                `Cache miss: called "getComputedStyle" with mismatched layoutDimensions on element and pseudoElt.
                To avoid additional expensive layout computations, pre-fetch the value during "on_parse_layout_with_dimensions_handlers"`,
                element,
                pseudoElt
            );
            this.callWithDimensions(() => {
                computedStyleProxy = this.computeStyleProxy(element, pseudoElt);
            }, layoutDimensions);
        } else {
            computedStyleProxy = this.computeStyleProxy(element, pseudoElt);
        }
        return new ComputedStyle(computedStyleProxy);
    }

    computeBoundingClientRect(cluster) {
        const boundingClientRectsMap = this.getNodeToBoundingClientRect();
        if (!boundingClientRectsMap.has(cluster)) {
            boundingClientRectsMap.set(cluster, this.getBoundingClientRectSnapshot(cluster));
        }
        return boundingClientRectsMap.get(cluster);
    }

    /**
     * Returns a cached view of `getBoundingClientRect`. The cache is long-lived if the node is in
     * the reference HTML (associated with a given dimensionsKey), because the reference dimensions
     * are fixed relative to that dimensionsKey, and the cache can be reused if
     * this function is called on the same node.
     * The cache is short-lived otherwise (it has its own scope), and a new call to this function
     * will essentially generate a call to `getBoundingClientRect`.
     * For non-element nodes, the returned boundingClientRect is the one generated from the range
     * around that node.
     *
     * @param {Node|Range} cluster
     * @returns {Object} cached bounding client rect
     */
    getBoundingClientRect(cluster, layoutDimensions = this.layoutDimensions) {
        const realmNode = cluster.commonAncestorContainer || cluster;
        if (cluster.nodeType && cluster.nodeType !== Node.ELEMENT_NODE) {
            cluster = this.getNodeClusterRange(cluster);
        }
        if (!this.config.referenceDocument.contains(realmNode)) {
            // Only the rect of a node/range inside the referenceDocument can be cached, as
            // the HTML and CSS content inside that document are fixed during conversion.
            return this.getBoundingClientRectSnapshot(cluster);
        }
        const nodeToBoundingClientRect = this.getNodeToBoundingClientRect(layoutDimensions);
        let boundingClientRect;
        if (nodeToBoundingClientRect.has(cluster)) {
            boundingClientRect = nodeToBoundingClientRect.get(cluster);
        } else if (layoutDimensions !== this.layoutDimensions) {
            console.warn(
                `Cache miss: called "getBoundingClientRect" with mismatched layoutDimensions on cluster.
                To avoid additional expensive layout computations, pre-fetch the value during "on_parse_layout_with_dimensions_handlers"`,
                cluster
            );
            this.callWithDimensions(() => {
                boundingClientRect = this.computeBoundingClientRect(cluster);
            }, layoutDimensions);
        } else {
            boundingClientRect = this.computeBoundingClientRect(cluster);
        }
        return boundingClientRect;
    }

    /**
     * Convenience function to get a single property value using the cache.
     * Prefer usage of `this.getComputedStyle` for elements outside of the
     * `reference` if multiple measures have to be made on the same element.
     */
    getStylePropertyValue(element, propertyName, layoutDimensions = this.layoutDimensions) {
        return this.getComputedStyle(element, layoutDimensions).getPropertyValue(propertyName);
    }

    /**
     * Convenience function to get a single DOMRect value using the cache.
     * Prefer usage of `this.getBoundingClientRect` for elements outside of the
     * `reference` if multiple measures have to be made on the same element.
     */
    getRectValue(element, propertyName, layoutDimensions = this.layoutDimensions) {
        return this.getBoundingClientRect(element, layoutDimensions)[propertyName];
    }

    /**
     * Custom `isBlock` function using the cache.
     * Determine if a node is to be considered as a Block for the purpose
     * of email layout.
     */
    isBlock(node) {
        if (!node || node.nodeType !== Node.ELEMENT_NODE || !node.isConnected) {
            return false;
        }
        if (node.nodeName === "BR") {
            // see html_editor isBlock for explanation (browser compatibility)
            return false;
        }
        const display = this.getStylePropertyValue(node, "display");
        if (display && display !== "none") {
            return !display.includes("inline") && display !== "contents";
        }
        return blockTagNames.includes(node.nodeName);
    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(MeasurementSnapshotPlugin.id, MeasurementSnapshotPlugin);
