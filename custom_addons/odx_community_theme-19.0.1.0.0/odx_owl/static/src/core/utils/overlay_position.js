/** @odoo-module **/

const VALID_SIDES = new Set(["top", "right", "bottom", "left"]);
const VALID_ALIGNS = new Set(["start", "center", "end", "fit", "middle"]);

function extractSide(position, fallback) {
    const candidate = String(position || fallback || "").split("-")[0];
    return VALID_SIDES.has(candidate) ? candidate : null;
}

function extractAlign(position, fallback) {
    const candidate = String(position || fallback || "").split("-")[1];
    return VALID_ALIGNS.has(candidate) ? candidate : null;
}

export function resolveOverlayPosition({ align, fallback = "bottom", position, side }) {
    const hasSideOverride = VALID_SIDES.has(side);
    const hasAlignOverride = VALID_ALIGNS.has(align);

    if (!hasSideOverride && !hasAlignOverride) {
        return position || fallback;
    }

    const resolvedSide = hasSideOverride
        ? side
        : extractSide(position, fallback) || "bottom";
    const resolvedAlign = hasAlignOverride ? align : extractAlign(position, fallback);

    if (!resolvedAlign || resolvedAlign === "center" || resolvedAlign === "middle") {
        return resolvedSide;
    }
    return `${resolvedSide}-${resolvedAlign}`;
}
