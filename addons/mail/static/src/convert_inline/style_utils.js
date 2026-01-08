import { parseSelector } from "@mail/convert_inline/css_selector_parser";

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

export function splitSelectorList(selector) {
    try {
        if (selector.indexOf(",") === -1) {
            return [selector].filter(Boolean);
        }
        return parseSelector(selector)
            .map((complexSelector) => complexSelector.selector)
            .filter(Boolean);
    } catch {
        return [];
    }
}
