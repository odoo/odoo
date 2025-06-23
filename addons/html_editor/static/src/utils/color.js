import { closestElement } from "@html_editor/utils/dom_traversal";
import { isColorGradient } from "@web/core/utils/colors";

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
 * @param {string|number} name
 * @returns {boolean}
 */
export function isColorCombinationName(name) {
    const number = parseInt(name);
    return !isNaN(number) && number % 100 !== 0;
}

export const TEXT_CLASSES_REGEX = /\btext-[^\s]*\b/;
export const BG_CLASSES_REGEX = /\bbg-[^\s]*\b/;
export const COLOR_COMBINATION_CLASSES_REGEX = /\bo_cc[0-9]+\b/g;

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

export function getTextColorOrClass(node) {
    if (!node) {
        return null;
    }
    if (node.style.color) {
        return { type: "style", value: node.style.color };
    }
    const textColorClass = [...node.classList].find((cls) => TEXT_CLASSES_REGEX.test(cls));
    if (textColorClass) {
        return { type: "class", value: textColorClass };
    }
    return null;
}
