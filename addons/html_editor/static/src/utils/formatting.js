import { normalizeCSSColor } from "@web/core/utils/colors";
import { BG_CLASSES_REGEX, COLOR_COMBINATION_CLASSES_REGEX, TEXT_CLASSES_REGEX } from "./color";
import { removeClass } from "./dom";
import { isBold, isItalic, isStrikeThrough, isUnderline } from "./dom_info";
import { closestElement, closestPath, findNode } from "./dom_traversal";
import { closestBlock, isBlock } from "./blocks";

/**
 * Array of all the classes used by the editor to change the font size.
 */
export const FONT_SIZE_CLASSES = [
    "display-1-fs",
    "display-2-fs",
    "display-3-fs",
    "display-4-fs",
    "h1-fs",
    "h2-fs",
    "h3-fs",
    "h4-fs",
    "h5-fs",
    "h6-fs",
    "base-fs",
    "small",
    "o_small-fs",
];

export const TEXT_STYLE_CLASSES = ["display-1", "display-2", "display-3", "display-4", "lead"];

/**
 * Inline decoration tags (<s>, <u>) that are split around and preserved as
 * wrappers inside a link when a link is created over decorated text.
 */
export const INLINE_DECORATION_TAGS = ["S", "U"];

export const formatsSpecs = {
    italic: {
        tagName: "em",
        isFormatted: isItalic,
        isTag: (node) => ["EM", "I"].includes(node.tagName),
        hasStyle: (node) => Boolean(node.style && node.style["font-style"]),
        addStyle: (node) => (node.style["font-style"] = "italic"),
        addNeutralStyle: (node) => (node.style["font-style"] = "normal"),
        removeStyle: (node) => removeStyle(node, "font-style"),
    },
    bold: {
        tagName: "strong",
        isFormatted: isBold,
        isTag: (node) => ["STRONG", "B"].includes(node.tagName),
        hasStyle: (node) => Boolean(node.style && node.style["font-weight"]),
        addStyle: (node) => (node.style["font-weight"] = "bolder"),
        addNeutralStyle: (node) => {
            node.style["font-weight"] = "normal";
        },
        removeStyle: (node) => removeStyle(node, "font-weight"),
    },
    underline: {
        tagName: "u",
        isFormatted: isUnderline,
        isTag: (node) => node.tagName === "U",
        hasStyle: (node) =>
            node.style &&
            (node.style["text-decoration"].includes("underline") ||
                node.style["text-decoration-line"].includes("underline")),
        addStyle: (node) => (node.style["text-decoration-line"] += " underline"),
        removeStyle: (node) =>
            removeStyle(
                node,
                node.style["text-decoration"].includes("underline")
                    ? "text-decoration"
                    : "text-decoration-line",
                "underline"
            ),
    },
    strikeThrough: {
        tagName: "s",
        isFormatted: isStrikeThrough,
        isTag: (node) => node.tagName === "S",
        hasStyle: (node) =>
            node.style &&
            (node.style["text-decoration"].includes("line-through") ||
                node.style["text-decoration-line"].includes("line-through")),
        addStyle: (node) => (node.style["text-decoration-line"] += " line-through"),
        removeStyle: (node) =>
            removeStyle(
                node,
                node.style["text-decoration"].includes("line-through")
                    ? "text-decoration"
                    : "text-decoration-line",
                "line-through"
            ),
    },
    fontSize: {
        isFormatted: (node) =>
            !!findNode(closestPath(node), (el) => el.style?.["font-size"], isBlock),
        hasStyle: (node) => node.style && node.style["font-size"],
        addStyle: (node, props) => {
            node.style["font-size"] = props.size;
            removeClass(node, ...FONT_SIZE_CLASSES);
        },
        removeStyle: (node) => removeStyle(node, "font-size"),
    },
    setFontSizeClassName: {
        isFormatted: (node, props) =>
            !!findNode(
                closestPath(node),
                (el) =>
                    props?.className
                        ? el.classList?.contains(props.className)
                        : FONT_SIZE_CLASSES.some((className) => el.classList?.contains(className)),
                isBlock
            ),
        hasStyle: (node, props) => FONT_SIZE_CLASSES.find((cls) => node.classList.contains(cls)),
        addStyle: (node, props) => {
            node.style.removeProperty("font-size");
            node.classList.add(props.className);
        },
        removeStyle: (node) => {
            removeStyle(node, "font-size");
            removeClass(node, ...FONT_SIZE_CLASSES, ...TEXT_STYLE_CLASSES);
        },
    },
};

function removeStyle(node, styleName, item) {
    if (item) {
        const newStyle = node.style[styleName]
            .split(" ")
            .filter((x) => x !== item)
            .join(" ");
        node.style[styleName] = newStyle || null;
    } else {
        node.style[styleName] = null;
    }
    if (node.getAttribute("style") === "") {
        node.removeAttribute("style");
    }
}

/**
 * @param {string} key
 * @param {object} htmlStyle
 * @returns {string}
 */
export function getCSSVariableValue(key, htmlStyle) {
    // Get trimmed value from the HTML element
    let value = htmlStyle.getPropertyValue(`--${key}`).trim();
    // If it is a color value, it needs to be normalized
    value = normalizeCSSColor(value);
    // Normally scss-string values are "printed" single-quoted. That way no
    // magic conversation is needed when customizing a variable: either save it
    // quoted for strings or non quoted for colors, numbers, etc. However,
    // Chrome has the annoying behavior of changing the single-quotes to
    // double-quotes when reading them through getPropertyValue...
    return value.replace(/"/g, "'");
}

/**
 * Key-value mapping to list converters from an unit A to an unit B.
 * - The key is a string in the format '$1-$2' where $1 is the CSS symbol of
 *   unit A and $2 is the CSS symbol of unit B.
 * - The value is a function that converts the received value (expressed in
 *   unit A) to another value expressed in unit B. Two other parameters is
 *   received: the css property on which the unit applies and the jQuery element
 *   on which that css property may change.
 */
const CSS_UNITS_CONVERSION = {
    "s-ms": () => 1000,
    "ms-s": () => 0.001,
    "rem-px": (htmlStyle) => parseFloat(htmlStyle["font-size"]),
    "px-rem": (htmlStyle) => 1 / parseFloat(htmlStyle["font-size"]),
    "%-px": () => -1, // Not implemented but should simply be ignored for now
    "px-%": () => -1, // Not implemented but should simply be ignored for now
};

/**
 * Converts the given numeric value expressed in the given css unit into
 * the corresponding numeric value expressed in the other given css unit.
 *
 * e.g. fct(400, 'ms', 's') -> 0.4
 *
 * @param {number} value
 * @param {string} unitFrom
 * @param {string} unitTo
 * @param {object} htmlStyle
 * @returns {number}
 */
export function convertNumericToUnit(value, unitFrom, unitTo, htmlStyle) {
    if (Math.abs(value) < Number.EPSILON || unitFrom === unitTo) {
        return value;
    }
    const converter = CSS_UNITS_CONVERSION[`${unitFrom}-${unitTo}`];
    if (converter === undefined) {
        throw new Error(`Cannot convert '${unitFrom}' units into '${unitTo}' units !`);
    }
    return value * converter(htmlStyle);
}

export function getHtmlStyle(document) {
    return document.defaultView.getComputedStyle(document.documentElement);
}

/**
 * Finds the font size to display for the current selection. We cannot rely
 * on the computed font-size only as font-sizes are responsive and we always
 * want to display the desktop (integer when possible) one.
 *
 * @param {Selection} sel The current selection.
 * @param {Document} document The document of the current selection.
 * @returns {Float} The font size to display.
 */
export function getFontSizeDisplayValue(sel, document) {
    const tagNameRelatedToFontSize = ["h1", "h2", "h3", "h4", "h5", "h6"];
    const styleClassesRelatedToFontSize = [
        "display-1",
        "display-2",
        "display-3",
        "display-4",
        "lead",
    ];
    const closestStartContainerEl = closestElement(sel.startContainer);
    const closestFontSizedEl = closestStartContainerEl.closest(`
        [style*='font-size'],
        ${FONT_SIZE_CLASSES.map((className) => `.${className}`)},
        ${styleClassesRelatedToFontSize.map((className) => `.${className}`)},
        ${tagNameRelatedToFontSize}
    `);
    let remValue;
    const htmlStyle = getHtmlStyle(document);
    if (closestFontSizedEl) {
        const useFontSizeInput = closestFontSizedEl.style.fontSize;
        if (useFontSizeInput) {
            // Use the computed value to always convert to px. However, this
            // currently does not check that the inline font-size is the one
            // actually having an effect (there could be an !important CSS rule
            // forcing something else).
            // TODO align with the behavior of the rest of the editor snippet
            // options.
            return parseFloat(getComputedStyle(closestStartContainerEl).fontSize);
        }
        // It's a class font size or a hN tag. We don't return the computed
        // font size because it can be different from the one displayed in
        // the toolbar because it's responsive.
        const fontSizeClass = FONT_SIZE_CLASSES.find((className) =>
            closestFontSizedEl.classList.contains(className)
        );
        let fsName;
        if (fontSizeClass) {
            fsName = fontSizeClass.substring(0, fontSizeClass.length - 3); // Without -fs
        } else {
            fsName =
                styleClassesRelatedToFontSize.find((className) =>
                    closestFontSizedEl.classList.contains(className)
                ) || closestFontSizedEl.tagName.toLowerCase();
        }
        remValue = parseFloat(getCSSVariableValue(`${fsName}-font-size`, htmlStyle));
    }
    const pxValue = remValue && convertNumericToUnit(remValue, "rem", "px", htmlStyle);
    return pxValue || parseFloat(getComputedStyle(closestStartContainerEl).fontSize);
}

/**
 * Checks if all classes in node are present in node2 (subset check)
 */
function hasClassesSubset(node, node2) {
    const getNodeClasses = (n) => (n || "").trim().split(/\s+/).filter(Boolean);
    const [nodeClasses, node2Classes] = [node, node2].map(getNodeClasses);
    return nodeClasses.every((cls) => node2Classes.includes(cls));
}

/**
 * Checks if a node is redundant based on its closest element with same tag,
 * or based on its parent's visual formatting / styles.
 *
 * @param {Node} node - The DOM node to evaluate.
 * @returns {boolean} True if the node is redundant, false otherwise.
 */
export function isRedundantElement(node) {
    // Ignore invalid nodes, non-elements, nodes without a parent, or nodes outside the document.
    if (!node || node.nodeType !== Node.ELEMENT_NODE || !node.parentElement || !node.isConnected) {
        return false;
    }

    // Semantic formatting tags without attributes whose visual formatting is
    // already inherited from their parent.
    if (!node.hasAttributes()) {
        const formatSpec = Object.values(formatsSpecs).find((spec) => spec.isTag?.(node));
        if (formatSpec) {
            return formatSpec.isFormatted(node.parentElement);
        }
        // Other tags without attributes are only redundant inside the same tag.
        return !!closestElement(node.parentElement, node.tagName);
    }

    // Check if inline styles or color classes are already provided by ancestors.
    if (node.tagName === "SPAN" || node.tagName === "FONT") {
        const hasStyle = node.hasAttribute("style");
        const hasClass = node.hasAttribute("class");

        // Only handle nodes with style or class, not exotic attributes (e.g. id).
        const expectedAttrCount = (hasStyle ? 1 : 0) + (hasClass ? 1 : 0);
        if (node.attributes.length !== expectedAttrCount) {
            return false;
        }

        // Check if inline styles match the parent's computed styles.
        // Bolder font weights stack numerically, so judge a format style
        // (bold, italic, ...) as boolean: the node and its parent must have it.
        let styleRedundant = !hasStyle;
        const formatSpec = Object.values(formatsSpecs).find(
            (spec) => spec.isTag && spec.hasStyle(node)
        );
        if (formatSpec) {
            styleRedundant =
                formatSpec.isFormatted(node) && formatSpec.isFormatted(node.parentElement);
        } else if (hasStyle) {
            const parentElement = node.parentElement;
            const nodeStyle = getComputedStyle(node);
            const parentStyle = getComputedStyle(parentElement);
            styleRedundant = [...node.style].every((styleKey) => {
                const nodeStyleValue = nodeStyle.getPropertyValue(styleKey);
                return nodeStyleValue && nodeStyleValue === parentStyle.getPropertyValue(styleKey);
            });
        }

        // Check if color classes are covered by a closer ancestor span/font.
        let classRedundant = !hasClass;
        if (hasClass) {
            const COLOR_CLASS_REGEXES = [
                TEXT_CLASSES_REGEX,
                BG_CLASSES_REGEX,
                COLOR_COMBINATION_CLASSES_REGEX,
            ];
            const nodeClasses = [...node.classList];
            // All classes must be recognized color classes.
            if (
                !nodeClasses.every((nodeClass) =>
                    COLOR_CLASS_REGEXES.some((colorRegex) => colorRegex.test(nodeClass))
                )
            ) {
                return false;
            }
            const blockBoundary = closestBlock(node);
            let ancestor = node.parentElement;
            while (ancestor && ancestor !== blockBoundary) {
                if (ancestor.tagName === "SPAN" || ancestor.tagName === "FONT") {
                    const ancestorClasses = [...ancestor.classList];
                    // Check if this node overrides a color class of the ancestor.
                    const isOverridingAncestor = nodeClasses.some((nodeClass) => {
                        const sameTypeRegex = COLOR_CLASS_REGEXES.find((colorRegex) =>
                            colorRegex.test(nodeClass)
                        );
                        return ancestorClasses.some(
                            (ancestorClass) =>
                                ancestorClass !== nodeClass && sameTypeRegex?.test(ancestorClass)
                        );
                    });
                    if (isOverridingAncestor) {
                        return false;
                    } else if (
                        hasClassesSubset(node.getAttribute("class"), ancestor.getAttribute("class"))
                    ) {
                        classRedundant = true;
                        break;
                    }
                }
                ancestor = ancestor.parentElement;
            }
        }
        return styleRedundant && classRedundant;
    }

    return false;
}
