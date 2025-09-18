// @ts-check

/** @module @web/core/utils/decorations - Maps decoration-* XML attributes to Bootstrap CSS classes */

/**
 * Maps a decoration name to its corresponding CSS class name.
 *
 * @param {string} decoration
 * @returns {string}
 */
export function getClassNameFromDecoration(decoration) {
    if (decoration === "bf") {
        return "fw-bold";
    } else if (decoration === "it") {
        return "fst-italic";
    }
    return `text-${decoration}`;
}

/**
 * Extracts decoration directives from an XML node's attributes.
 *
 * @param {Element} rootNode
 * @returns {{ class: string, condition: string }[]}
 */
export function getDecoration(rootNode) {
    const decorations = [];
    for (const name of rootNode.getAttributeNames()) {
        if (name.startsWith("decoration-")) {
            decorations.push({
                class: getClassNameFromDecoration(name.replace("decoration-", "")),
                condition: rootNode.getAttribute(name),
            });
        }
    }
    return decorations;
}
