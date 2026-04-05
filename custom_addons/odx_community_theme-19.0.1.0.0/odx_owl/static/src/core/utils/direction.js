/** @odoo-module **/

export function resolveDirection(explicitDirection) {
    if (explicitDirection === "rtl" || explicitDirection === "ltr") {
        return explicitDirection;
    }
    // Check html[dir] first, then fall back to computed direction on body.
    // Odoo sets direction via CSS on body (not html[dir] attribute) for
    // RTL languages like Arabic.
    const doc = globalThis.document;
    if (doc?.documentElement?.dir) {
        return doc.documentElement.dir;
    }
    if (doc?.body) {
        const computed = globalThis.getComputedStyle?.(doc.body)?.direction;
        if (computed === "rtl" || computed === "ltr") {
            return computed;
        }
    }
    return "ltr";
}

export function isRtlDirection(explicitDirection) {
    return resolveDirection(explicitDirection) === "rtl";
}
