/**
 * Checks whether the given element is inside a social snippet.
 *
 * @param {HTMLElement} editingElement
 * @returns {boolean} Whether the element is inside a social snippet.
 */
export function isInsideSocialSnippet(editingElement) {
    return Boolean(editingElement.closest(".s_social_media") || editingElement.closest(".s_share"));
}
