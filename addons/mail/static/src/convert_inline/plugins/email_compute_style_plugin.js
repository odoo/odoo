import { BasePlugin } from "@html_editor/base_plugin";
import { registry } from "@web/core/registry";
import { generateLonghands } from "@mail/convert_inline/style_utils";

const BACKGROUND_VARIANTS = ["color", "image", "repeat", "size"];
const CONTOUR_VARIANTS = ["width", "style", "color"];
const DIRECTION_VARIANTS = ["top", "right", "bottom", "left"];
const FONT_VARIANTS = ["family", "size", "style", "weight"];

export class EmailComputeStylePlugin extends BasePlugin {
    static id = "computeStyle";
    static shared = [
        "getComputedStyle",
        "getStylePropertyValue",
        "getHeight",
        "getWidth",
        "registerStyleProperty",
    ];

    resources = {
        // typical shorthands for emails (prefer usage of longhand names for
        // these properties). They are recorded by default in a getComputedStyle
        // snapshot
        shorthand_to_longhand_properties: {
            background: new Set(generateLonghands("background", [BACKGROUND_VARIANTS])),
            border: new Set(generateLonghands("border", [DIRECTION_VARIANTS, CONTOUR_VARIANTS])),
            font: new Set(generateLonghands("font", [FONT_VARIANTS])),
            margin: new Set(generateLonghands("margin", [DIRECTION_VARIANTS])),
            outline: new Set(generateLonghands("outline", [CONTOUR_VARIANTS])),
            padding: new Set(generateLonghands("padding", [DIRECTION_VARIANTS])),
        },
        // longhands recorded by default in a getComputedStyle snapshot
        longhand_properties: [
            "border-collapse",
            "box-sizing",
            "color",
            "display",
            "height",
            "line-height",
            "position",
            "text-decoration",
            "text-transform",
            "text-align",
            "vertical-align",
            "width",
        ],
        update_layout_dimensions_handlers: this.onUpdateLayoutDimensions.bind(this),
    };

    setup() {
        this.properties = new Set(); // properties to register in a snapshot
        this.computedStylesMap = new Map(); // dimensions to WeakMap of element to computed snapshot proxy
        this.dimensionsKey = "undefined";
        this.computedStylesMap.set(this.dimensionsKey, new WeakMap());
        this.setupShorthandToLonghand();
        this.setupProperties();
    }

    setupShorthandToLonghand() {
        this.shorthandToLonghand = this.getResource("shorthand_to_longhand_properties").reduce(
            (shortHandToLonghand, current) => {
                for (const property in current) {
                    shortHandToLonghand[property] = current[property].union(
                        shortHandToLonghand[property] ?? new Set()
                    );
                }
                return shortHandToLonghand;
            },
            {}
        );
    }

    setupProperties() {
        for (const propertyName in this.shorthandToLonghand) {
            this.registerStyleProperty(propertyName);
        }
        const longhandProperties = this.getResource("longhand_properties");
        for (const propertyName of longhandProperties) {
            this.registerStyleProperty(propertyName);
        }
    }

    onUpdateLayoutDimensions({ width }) {
        this.dimensionsKey = `${width}`;
        if (!this.computedStylesMap.has(this.dimensionsKey)) {
            this.computedStylesMap.set(this.dimensionsKey, new WeakMap());
        }
    }

    cachedComputedStyleProxyHandler(element) {
        return {
            set: () => false,
            deleteProperty: () => false,
            get: (target, key, receiver) => {
                if (typeof key === "string" && !(key in target)) {
                    this.registerStyleProperty(key);
                    this.getStaticStyle(element, target);
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
        if (!this.properties.has(propertyName)) {
            this.properties.add(propertyName);
        }
    }

    getStaticStyle(element, staticStyle = {}) {
        const computedStyle = element.ownerDocument.defaultView.getComputedStyle(element);
        for (const propertyName of this.properties) {
            if (!(propertyName in staticStyle)) {
                staticStyle[propertyName] = computedStyle.getPropertyValue(propertyName);
            }
        }
        return staticStyle;
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
     * @returns {Object} cached style
     */
    getComputedStyle(element) {
        if (this.config.referenceDocument.contains(element)) {
            // Only the style of an element inside the referenceDocument can be cached, as
            // the HTML and CSS content inside that document are fixed during conversion.
            const cachedStyle =
                this.computedStylesMap.get(this.dimensionsKey).get(element) ??
                new Proxy({}, this.cachedComputedStyleProxyHandler(element));
            this.computedStylesMap.get(this.dimensionsKey).set(element, cachedStyle);
            return cachedStyle;
        }
        return new Proxy({}, this.cachedComputedStyleProxyHandler(element));
    }

    /**
     * Convenience function to get a single property value using the cache.
     * Prefer usage of `this.getComputedStyle` for elements outside of the
     * `reference` if multiple measures have to be made on the same element.
     */
    getStylePropertyValue(element, propertyName) {
        return this.getComputedStyle(element)[propertyName];
    }

    /**
     * @param {HtmlElement} element
     * @returns {Number} width
     */
    getWidth(element) {
        return parseFloat(this.getStylePropertyValue(element, "width")) || 0;
    }

    /**
     * @param {HtmlElement} element
     * @returns {Number} height
     */
    getHeight(element) {
        return parseFloat(this.getStylePropertyValue(element, "height")) || 0;
    }
}

registry
    .category("mail-html-conversion-plugins")
    .add(EmailComputeStylePlugin.id, EmailComputeStylePlugin);
