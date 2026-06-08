/**
 * @import { DependencyInManifest } from "@mail/utils/common/format"
 * ⚠️ {@link DependencyInManifest}
 */

import { markup } from "@odoo/owl";

import { htmlJoin } from "@web/core/utils/html";

/**
 * Returns whether the given tag is a void HTML element.
 *
 * @param {string} tag
 */
function isVoidElement(tag) {
    // outerHTML represents non-void elements with both opening and closing tags,
    // so their length is strictly greater than the tag name length + 2 (for <>).
    return document.createElement(tag).outerHTML.length === tag.length + 2;
}

/**
 * @param {Node} node
 * @param {Object} [options={}]
 * @param {boolean} [options.innerOnly=false]
 * @return {string|ReturnType<markup>}
 */
function escapeNode(node, { innerOnly = false } = {}) {
    if (!node || node.nodeType === Node.COMMENT_NODE) {
        return "";
    }
    if (node.nodeType === Node.TEXT_NODE) {
        return innerOnly ? "" : node.textContent;
    }
    const children = htmlJoin(Array.from(node.childNodes).map((node) => escapeNode(node)));
    if (innerOnly) {
        return children;
    }
    const tag = node.tagName.toLowerCase();
    const attributeList = Array.from(node.attributes);
    if (attributeList.length === 0) {
        if (isVoidElement(tag)) {
            return markup`<${tag}>`;
        }
        return markup`<${tag}>${children}</${tag}>`;
    }
    const attributes = htmlJoin(
        attributeList.map((attr) => markup`${attr.name}="${attr.value}"`),
        " "
    );
    if (isVoidElement(tag)) {
        return markup`<${tag} ${attributes}>`;
    }
    return markup`<${tag} ${attributes}>${children}</${tag}>`;
}

/**
 * Safely gets innerHTML of the given Element.
 *
 * @param {Element} element
 * @returns {string|ReturnType<markup>}
 */
export function getInnerHtml(element) {
    return escapeNode(element, { innerOnly: true });
}

/**
 * Safely gets outerHTML of the given Element.
 *
 * @param {Element} element
 * @returns {string|ReturnType<markup>}
 */
export function getOuterHtml(element) {
    return escapeNode(element);
}
