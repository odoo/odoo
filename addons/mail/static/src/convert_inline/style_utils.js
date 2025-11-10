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

export function splitSelectorAroundCommasOutsideParentheses(selector) {
    if (selector.indexOf(",") === -1) {
        return [selector].filter(Boolean);
    }
    const result = [];
    let start = 0;
    let depth = 0;
    let inString;
    for (let i = 0; i < selector.length; i++) {
        const char = selector[i];
        if (inString) {
            if (char === inString && selector[i - 1] !== "\\") {
                inString = undefined;
            }
            continue;
        }
        switch (char) {
            case "'":
            case '"':
                inString = char;
                break;
            case "(":
                depth++;
                break;
            case ")":
                depth--;
                if (depth < 0) {
                    return [selector];
                }
                break;
            case ",":
                if (depth === 0) {
                    result.push(selector.slice(start, i));
                    start = i + 1;
                }
                break;
        }
    }
    if (depth > 0) {
        return [selector];
    }
    result.push(selector.slice(start));
    return result.filter(Boolean);
}
