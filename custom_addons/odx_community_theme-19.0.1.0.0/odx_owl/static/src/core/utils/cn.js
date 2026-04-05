/** @odoo-module **/

function flattenValue(value, result) {
    if (!value) {
        return;
    }
    if (typeof value === "string") {
        result.push(value);
        return;
    }
    if (Array.isArray(value)) {
        for (const item of value) {
            flattenValue(item, result);
        }
        return;
    }
    if (typeof value === "object") {
        for (const [key, enabled] of Object.entries(value)) {
            if (enabled) {
                result.push(key);
            }
        }
    }
}

export function cn(...values) {
    const result = [];
    for (const value of values) {
        flattenValue(value, result);
    }
    return [...new Set(result.join(" ").split(/\s+/).filter(Boolean))].join(" ");
}
