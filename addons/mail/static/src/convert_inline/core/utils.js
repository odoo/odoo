import { StyleInfo } from "./style_models";

export const BACKGROUND_VARIANTS = ["color", "image", "repeat", "size"];
export const CONTOUR_VARIANTS = ["width", "style", "color"];
export const DIRECTION_VARIANTS = ["top", "right", "bottom", "left"];
export const FONT_VARIANTS = ["family", "size", "style", "weight"];
export const DOM_RECT_PROPERTIES = ["x", "y", "width", "height", "top", "right", "bottom", "left"];

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
    return Object.assign({}, attributes, {
        class: [...classNames.values()].join(" ") || undefined,
        style: styleInfo.toString() || undefined,
    });
}
