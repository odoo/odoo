import { markup } from "@odoo/owl";

import { escape } from "@web/core/utils/strings";

const Markup = markup().constructor;

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
    const div = document.createElement("div");
    setElementContent(div, content);
    return div.textContent.trim() === "";
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
