import { markup } from "@odoo/owl";

import { htmlEscape, setElementContent } from "@web/core/utils/html";

/**
 * Safely creates a Document fragment from content. If content was flagged as safe HTML using
 * `markup()` it is parsed as HTML. Otherwise it is escaped and parsed as text.
 *
 * @param {string|ReturnType<markup>} content
 */
export function createDocumentFragmentFromContent(content) {
    const div = document.createElement("div");
    setElementContent(div, content);
    return new DOMParser().parseFromString(div.innerHTML, "text/html");
}

/**
 * Applies list join on content and returns a markup result built for HTML.
 *
 * @param {Array<string|ReturnType<markup>>} args
 * @returns {ReturnType<markup>}
 */
export function htmlJoin(...args) {
    return markup(args.map((arg) => htmlEscape(arg)).join(""));
}

/**
 * Applies string replace on content and returns a markup result built for HTML.
 *
 * @param {string|ReturnType<markup>} content
 * @param {string | RegExp} search
 * @param {string} replacement
 * @returns {ReturnType<markup>}
 */
export function htmlReplace(content, search, replacement) {
    content = htmlEscape(content);
    if (typeof search === "string" || search instanceof String) {
        search = htmlEscape(search);
    }
    replacement = htmlEscape(replacement);
    return markup(content.replace(search, replacement));
}

/**
 * Applies string trim on content and returns a markup result built for HTML.
 *
 * @param {string|ReturnType<markup>} content
 * @returns {string|ReturnType<markup>}
 */
export function htmlTrim(content) {
    content = htmlEscape(content);
    return markup(content.trim());
}
