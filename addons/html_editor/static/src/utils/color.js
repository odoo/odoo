import { closestElement } from "@html_editor/utils/dom_traversal";

export const COLOR_PALETTE_COMPATIBILITY_COLOR_NAMES = [
    "primary",
    "secondary",
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
    "success",
    "info",
    "warning",
    "danger",
];

/**
 * Colors of the default palette, used for substitution in shapes/illustrations.
 * key: number of the color in the palette (ie, o-color-<1-5>)
 * value: color hex code
 */
export const DEFAULT_PALETTE = {
    1: "#3AADAA",
    2: "#7C6576",
    3: "#F6F6F6",
    4: "#FFFFFF",
    5: "#383E45",
};

/**
 * These constants are colors that can be edited by the user when using
 * web_editor in a website context. We keep track of them so that color
 * palettes and their preview elements can always have the right colors
 * displayed even if website has redefined the colors during an editing
 * session.
 *
 * @type {string[]}
 */
export const EDITOR_COLOR_CSS_VARIABLES = [...COLOR_PALETTE_COMPATIBILITY_COLOR_NAMES];

// o-cc and o-colors
for (let i = 1; i <= 5; i++) {
    EDITOR_COLOR_CSS_VARIABLES.push(`o-color-${i}`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-bg`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-bg-gradient`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-headings`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-text`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-btn-primary`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-btn-primary-text`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-btn-secondary`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-btn-secondary-text`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-btn-primary-border`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-btn-secondary-border`);
}

// Grays
for (let i = 100; i <= 900; i += 100) {
    EDITOR_COLOR_CSS_VARIABLES.push(`${i}`);
}

/**
 * Takes a color (rgb, rgba or hex) and returns its hex representation. If the
 * color is given in rgba, the background color of the node whose color we're
 * converting is used in conjunction with the alpha to compute the resulting
 * color (using the formula: `alpha*color + (1 - alpha)*background` for each
 * channel).
 *
 * @param {string} rgb
 * @param {HTMLElement} [node]
 * @returns {string} hexadecimal color (#RRGGBB)
 */
export function rgbToHex(rgb = "", node = null) {
    if (rgb.startsWith("#")) {
        return rgb;
    } else if (rgb.startsWith("rgba")) {
        const values = rgb.match(/[\d.]{1,5}/g) || [];
        const alpha = parseFloat(values.pop());
        // Retrieve the background color.
        let bgRgbValues = [];
        if (node) {
            let bgColor = getComputedStyle(node).backgroundColor;
            if (bgColor.startsWith("rgba")) {
                // The background color is itself rgba so we need to compute
                // the resulting color using the background color of its
                // parent.
                bgColor = rgbToHex(bgColor, node.parentElement);
            }
            if (bgColor && bgColor.startsWith("#")) {
                bgRgbValues = (bgColor.match(/[\da-f]{2}/gi) || []).map((val) => parseInt(val, 16));
            } else if (bgColor && bgColor.startsWith("rgb")) {
                bgRgbValues = (bgColor.match(/[\d.]{1,5}/g) || []).map((val) => parseInt(val));
            }
        }
        bgRgbValues = bgRgbValues.length ? bgRgbValues : [255, 255, 255]; // Default to white.

        return (
            "#" +
            values
                .map((value, index) => {
                    const converted = Math.floor(
                        alpha * parseInt(value) + (1 - alpha) * bgRgbValues[index]
                    );
                    const hex = parseInt(converted).toString(16);
                    return hex.length === 1 ? "0" + hex : hex;
                })
                .join("")
        );
    } else {
        return (
            "#" +
            (rgb.match(/\d{1,3}/g) || [])
                .map((x) => {
                    x = parseInt(x).toString(16);
                    return x.length === 1 ? "0" + x : x;
                })
                .join("")
        );
    }
}

/**
 * @param {string|number} name
 * @returns {boolean}
 */
export function isColorCombinationName(name) {
    const number = parseInt(name);
    return !isNaN(number) && number % 100 !== 0;
}

/**
 * @param {string} [value]
 * @returns {boolean}
 */
export function isColorGradient(value) {
    return value && value.includes("-gradient(");
}

export const TEXT_CLASSES_REGEX = /\btext-[^\s]*\b/;
export const BG_CLASSES_REGEX = /\bbg-[^\s]*\b/;

/**
 * Returns true if the given element has a visible color (fore- or
 * -background depending on the given mode).
 *
 * @param {Element} element
 * @param {string} mode 'color' or 'backgroundColor'
 * @returns {boolean}
 */
export function hasColor(element, mode) {
    const style = element.style;
    const parent = element.parentNode;
    const classRegex = mode === "color" ? TEXT_CLASSES_REGEX : BG_CLASSES_REGEX;
    if (isColorGradient(style["background-image"])) {
        if (element.classList.contains("text-gradient")) {
            if (mode === "color") {
                return true;
            }
        } else {
            if (mode !== "color") {
                return true;
            }
        }
    }
    return (
        (style[mode] &&
            style[mode] !== "inherit" &&
            style[mode] !== "initial" &&
            (!parent || style[mode] !== parent.style[mode])) ||
        (classRegex.test(element.className) &&
            (!parent || getComputedStyle(element)[mode] !== getComputedStyle(parent)[mode]))
    );
}

/**
 * Returns true if any given nodes has a visible color (fore- or
 * -background depending on the given mode).
 *
 * @param {array} nodes
 * @param {string} mode 'color' or 'backgroundColor'
 * @returns {boolean}
 */
export function hasAnyNodesColor(nodes, mode) {
    for (const node of nodes) {
        if (hasColor(closestElement(node), mode)) {
            return true;
        }
    }
    return false;
}
