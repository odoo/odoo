import { htmlEscape, markup } from "@odoo/owl";

/**
 * Safely creates a Document fragment from content. If content was flagged as safe HTML using
 * `markup()` it is parsed as HTML. Otherwise it is escaped and parsed as text.
 *
 * @param {string|ReturnType<markup>} content
 */
export function createDocumentFragmentFromContent(content) {
    return new document.defaultView.DOMParser().parseFromString(htmlEscape(content), "text/html");
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
    if (search instanceof RegExp && !(replacement instanceof Function)) {
        throw new Error("htmlReplace: replacement must be a function when search is a RegExp.");
    }
    if (typeof search === "string" || search instanceof String) {
        search = htmlEscape(search);
    }
    const safeReplacement =
        replacement instanceof Function
            ? (...args) => htmlEscape(replacement(...args))
            : htmlEscape(replacement);
    // markup: escaped (or safe) content with escaped (or safe) replacements
    return markup(htmlEscape(content).replace(search, safeReplacement));
}

/**
 * Applies string replaceAll on content and returns a markup result built for HTML.
 *
 * @param {string|ReturnType<markup>} content
 * @param {string | RegExp} search
 * @param {string|(match: string) => string|ReturnType<markup>} replacement
 * @returns {ReturnType<markup>}
 */
export function htmlReplaceAll(content, search, replacement) {
    if (search instanceof RegExp && !(replacement instanceof Function)) {
        throw new Error("htmlReplaceAll: replacement must be a function when search is a RegExp.");
    }
    if (typeof search === "string" || search instanceof String) {
        search = htmlEscape(search);
    }
    const safeReplacement =
        replacement instanceof Function
            ? (...args) => htmlEscape(replacement(...args))
            : htmlEscape(replacement);
    // markup: escaped (or safe) content with escaped (or safe) replacements
    return markup(htmlEscape(content).replaceAll(search, safeReplacement));
}

/**
 * Applies string trim on content and returns a markup result built for HTML.
 *
 * @param {string|ReturnType<markup>} content
 * @returns {string|ReturnType<markup>}
 */
export function htmlTrim(content) {
    // markup: escaped (or safe) content
    return markup(htmlEscape(content).trim());
}
