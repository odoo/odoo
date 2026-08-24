import { StyleInfo } from "./style_models";

export const BLOCKED_PSEUDO_CLASSES = new Set([
    "active",
    "focus",
    "focus-within",
    "hover",
    "link",
    "target",
    "visited",
]);
export const INDIRECT_CSS_PROPERTY_VALUES = new Set([
    "inherit",
    "initial",
    "unset",
    "revert",
    "revert-layer",
]);
// TODO EGGMAIL: inline-block is not supported in MSO, investigate if this needs
// custom handling
export const ALLOWED_CSS_DISPLAY_VALUES = new Set(["block", "inline", "inline-block", "none"]);
export const BLOCKED_CSS_POSITION_VALUES = new Set(["absolute", "sticky", "fixed"]);
export const OPPOSITE_DIRECTION = {
    left: "right",
    right: "left",
    bottom: "top",
    top: "bottom",
};

export const BACKGROUND_VARIANTS = ["color", "image", "repeat", "size"];
export const CONTOUR_VARIANTS = ["width", "style", "color"];
export const DIRECTION_VARIANTS = ["top", "right", "bottom", "left"];
export const FONT_VARIANTS = ["family", "size", "style", "weight"];
export const DOM_RECT_PROPERTIES = ["x", "y", "width", "height", "top", "right", "bottom", "left"];

export const DIMENSIONS = {
    DESKTOP: Object.freeze({
        width: 1320,
        height: 1000,
    }),
    MOBILE: Object.freeze({
        width: 360,
        height: 1000,
    }),
    DESKTOP_MOBILE_BREAKPOINT: Object.freeze({
        width: 768,
    }),
};

export const ALLOWED_MOBILE_MARGINS_SIZES = [8, 16, 32];

/**
 * @param {string} propertyName shorthand property e.g. "border"
 * @param {Array<Array<string>>} suffixArrays e.g. [["top", "right"], ["width", "color"]]
 * @returns {Array<string>} longhand properties ordered by asc. suffixes and desc. suffixArrays
 *          e.g. ["border-top-width", "border-bottom-width", "border-top-color", "border-bottom-color"]
 */
export function generateLonghands(propertyName, suffixArrays = []) {
    const result = [];
    const suffixes = [...suffixArrays].pop();
    if (!suffixes) {
        result.push(propertyName);
        return result;
    }
    for (const suffix of suffixes) {
        result.push(
            ...generateLonghands(
                `${propertyName}`,
                suffixArrays.slice(0, suffixArrays.length - 1)
            ).map((propertyName) => `${propertyName}-${suffix}`)
        );
    }
    return result;
}

export function renderAttributes({
    attributes = {},
    classNames = new Set(),
    styleInfo = new StyleInfo(),
} = {}) {
    const renderedAttributes = Object.assign({}, attributes, {
        class: [...classNames.values()].join(" ") || undefined,
        style: styleInfo.toString() || undefined,
    });
    for (const [name, value] of Object.entries(renderedAttributes)) {
        if (value === undefined) {
            delete renderedAttributes[name];
        }
    }
    return renderedAttributes;
}
