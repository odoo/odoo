import { markup } from "@odoo/owl";

import { escape } from "@web/core/utils/strings";
import { formatList } from "../l10n/utils";

const Markup = markup().constructor;

/**
 * Safely creates an element with the given content. If content was flagged as safe HTML using
 * `markup()` it is set as innerHTML. Otherwise it is set as text.
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
 * Escapes content for HTML. Content is unchanged if it is already a Markup.
 *
 * @param {string|ReturnType<markup>} content
 * @returns {ReturnType<markup>}
 */
export function htmlEscape(content) {
    return content instanceof Markup ? content : markup(escape(content));
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
 * Safely sets content on element. If content was flagged as safe HTML using `markup()` it is set as
 * innerHTML. Otherwise it is set as text.
 *
 * @param {Element} element
 * @param {string|ReturnType<markup>} content
 */
export function setElementContent(element, content) {
    if (content instanceof Markup) {
        element.innerHTML = content;
    } else {
        element.textContent = content;
    }
}
