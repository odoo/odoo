/** @odoo-module **/

let idCounter = 0;

export function nextId(prefix = "odx") {
    idCounter += 1;
    return `${prefix}-${idCounter}`;
}

export function sanitizeIdFragment(value) {
    return String(value)
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9_-]+/g, "-")
        .replace(/^-+|-+$/g, "");
}
