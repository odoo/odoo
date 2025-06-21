/** @odoo-module **/

const CSS_COLOR_REGEX = /^((#[A-F0-9]{3})|(#[A-F0-9]{6})|((hsl|rgb)a?\(\s*(?:(\s*\d{1,3}%?\s*),?){3}(\s*,[0-9.]{1,4})?\))|)$/i;
const colorMap = new Map();

export function getColor(key) {
    if (!key) {
        return false;
    }
    if (colorMap.has(key)) {
        return colorMap.get(key);
    }

    // check if the key is a css color
    if (typeof key === "string" && key.match(CSS_COLOR_REGEX)) {
        colorMap.set(key, key);
    } else if (typeof key === "number") {
        colorMap.set(key, ((key - 1) % 55) + 1);
    } else {
        colorMap.set(key, (((colorMap.size + 1) * 5) % 24) + 1);
    }

    return colorMap.get(key);
}
