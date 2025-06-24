import { htmlEscape, markup } from "@odoo/owl";

import { formatList } from "../l10n/utils";

const Markup = markup().constructor;

/**
 * Safely creates a Document fragment from content. If content was flagged as safe HTML using
 * `markup` it is parsed as HTML. Otherwise it is escaped and parsed as text.
 *
 * @param {string|ReturnType<markup>} content
 */
export function createDocumentFragmentFromContent(content) {
    return new document.defaultView.DOMParser().parseFromString(htmlEscape(content), "text/html");
}

/**
 * Safely creates an element with the given content. If content was flagged as safe HTML using
 * `markup` it is set as innerHTML. Otherwise it is set as text.
 *
 * @param {string} elementName
 * @param {string|ReturnType<markup>} content
 * @returns {Element}
 */
export function createElementWithContent(elementName, content) {
    const element = document.createElement(elementName);
    setElementContent(element, content);
    return element;
}

/**
 * Same behavior as formatList, but produces safe HTML. If the values are flagged as safe HTML using
 * `markup()` they are set as it is. Otherwise they are escaped.
 *
 * @param {Array<string|ReturnType<markup>>} list The array of values to format into a list.
 * @param {Object} [param0]
 * @param {string} [param0.localeCode] The locale to use (e.g. en-US).
 * @param {"standard"|"standard-short"|"or"|"or-short"|"unit"|"unit-short"|"unit-narrow"} [param0.style="standard"] The style to format the list with.
 * @returns {ReturnType<markup>} The formatted list.
 */
export function htmlFormatList(list, ...args) {
    return markup(
        formatList(
            Array.from(list, (val) => htmlEscape(val).toString()),
            ...args
        )
    );
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
    content = htmlEscape(content);
    if (typeof search === "string" || search instanceof String) {
        search = htmlEscape(search);
    }
    const safeReplacement =
        replacement instanceof Function
            ? (...args) => htmlEscape(replacement(...args))
            : htmlEscape(replacement);
    // markup: content and replacement are escaped (or markup), replace is considered safe
    return markup(content.replace(search, safeReplacement));
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
    content = htmlEscape(content);
    if (typeof search === "string" || search instanceof String) {
        search = htmlEscape(search);
    }
    const safeReplacement =
        replacement instanceof Function
            ? (...args) => htmlEscape(replacement(...args))
            : htmlEscape(replacement);
    // markup: content and replacement are escaped (or markup), replaceAll is considered safe
    return markup(content.replaceAll(search, safeReplacement));
}

/**
 * Applies list join on content and returns a markup result built for HTML.
 *
 * @param {Array<string|ReturnType<markup>>} args
 * @returns {ReturnType<markup>}
 */
export function htmlJoin(list, separator = "") {
    // markup: args and separator are escaped (or markup), join is considered safe
    return markup(list.map((arg) => htmlEscape(arg)).join(htmlEscape(separator)));
}

/**
 * Applies string trim on content and returns a markup result built for HTML.
 *
 * @param {string|ReturnType<markup>} content
 * @returns {string|ReturnType<markup>}
 */
export function htmlTrim(content) {
    content = htmlEscape(content);
    // markup: content is escaped (or markup), trim is considered safe
    return markup(content.trim());
}

/**
 * Checks if a html content is empty. If there are only formatting tags
 * with style attributes or a void content. Famous use case is
 * '<p style="..." class=".."><br></p>' added by some web editor(s).
 * Note that because the use of this method is limited, we ignore the cases
 * like there's one <img> tag in the content. In such case, even if it's the
 * actual content, we consider it empty.
 *
 * @param {string|ReturnType<markup>} content
 * @returns {boolean} true if no content found or if containing only formatting tags
 */
export function isHtmlEmpty(content = "") {
    return createElementWithContent("div", content).textContent.trim() === "";
}

/**
 * Safely sets content on element. If content was flagged as safe HTML using `markup` it is set as
 * innerHTML. Otherwise it is set as text.
 *
 * @param {Element} element
 * @param {string|ReturnType<markup>} content
 */
export function setElementContent(element, content) {
    if (content instanceof Markup) {
        // innerHTML: content is markup
        element.innerHTML = content;
    } else {
        element.textContent = content;
    }
}
