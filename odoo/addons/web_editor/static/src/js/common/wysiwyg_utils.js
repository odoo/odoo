/** @odoo-module **/

export function isImg(node) {
    return (node && (node.nodeName === "IMG" || (node.className && node.className.match(/(^|\s)(media_iframe_video|o_image|fa)(\s|$)/i))));
}

/**
 * Returns a list of all the ancestors nodes of the provided node.
 *
 * @param {Node} node
 * @param {Node} [stopElement] include to prevent bubbling up further than the stopElement.
 * @returns {HTMLElement[]}
 */
export function ancestors(node, stopElement) {
    if (!node || !node.parentElement || node === stopElement) return [];
    return [node.parentElement, ...ancestors(node.parentElement, stopElement)];
}