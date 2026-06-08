import { normalizeCSSColor } from "@web/core/utils/colors";
import { closestElement, findUpTo } from "./dom_traversal";

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

export const DEFAULT_FONT_SIZE_CLASSES = [
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "o_default_font_size",
];

export const FORMATTABLE_TAGS = ["SPAN", "FONT", "B", "STRONG", "I", "EM", "U", "S", "CODE"];

export function removeStyle(node, styleName, item) {
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
 *   received: the css property on which the unit applies and the element
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
    const closestStartContainerEl = closestElement(sel.startContainer);
    const closestFontSizedEl = findUpTo(
        closestStartContainerEl,
        closestStartContainerEl.closest(".o_default_font_size"),
        (n) =>
            n.matches(`
                [style*='font-size'],
                ${FONT_SIZE_CLASSES.map((className) => `.${className}`)},
                ${TEXT_STYLE_CLASSES.map((className) => `.${className}`)},
                ${tagNameRelatedToFontSize}
            `)
    );
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
                TEXT_STYLE_CLASSES.find((className) =>
                    closestFontSizedEl.classList.contains(className)
                ) || closestFontSizedEl.tagName.toLowerCase();
        }
        remValue = parseFloat(getCSSVariableValue(`${fsName}-font-size`, htmlStyle));
    }
    const pxValue = remValue && convertNumericToUnit(remValue, "rem", "px", htmlStyle);
    return pxValue || parseFloat(getComputedStyle(closestStartContainerEl).fontSize);
}

export function getFontSizeOrClass(node) {
    if (!node) {
        return null;
    }

    if (node.style.fontSize) {
        return { type: "font-size", value: node.style.fontSize };
    }

    const fontSizeClass = FONT_SIZE_CLASSES.find((cls) => node.classList.contains(cls));
    if (fontSizeClass) {
        return { type: "class", value: fontSizeClass };
    }
    return null;
}
