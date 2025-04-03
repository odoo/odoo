import { htmlEscape, markup } from "@odoo/owl";

import { sprintf } from "@web/core/utils/strings";
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
 * Gets innerHTML of the given Element, and wraps it in a Markup object as innerHTML always returns
 * safe text (assuming the element was safely built).
 *
 * @param {Element} element
 * @returns {ReturnType<markup>}
 */
export function getInnerHtml(element) {
    // markup: innerHTML is safe (assuming element was safely built)
    return markup(element?.innerHTML ?? "");
}

/**
 * Gets outerHTML of the given Element, and wraps it in a Markup object as outerHTML always returns
 * safe text (assuming the element was safely built).
 *
 * @param {Element} element
 * @returns {ReturnType<markup>}
 */
export function getOuterHtml(element) {
    // markup: outerHTML is safe (assuming element was safely built)
    return markup(element?.outerHTML ?? "");
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
    // markup: escaped values (assuming formatList itself is safe)
    return markup(
        formatList(
            Array.from(list, (val) => htmlEscape(val).toString()),
            ...args
        )
    );
}

/**
 * Applies list join on content and returns a markup result built for HTML.
 *
 * @param {Array<string|ReturnType<markup>>} args
 * @returns {ReturnType<markup>}
 */
export function htmlJoin(list, separator = "") {
    // markup: escaped values and separator (assuming join itself is safe)
    return markup(list.map((arg) => htmlEscape(arg)).join(htmlEscape(separator)));
}

/**
 * Same behavior as sprintf, but produces safe HTML. If the string or values are flagged as safe HTML
 * using `markup()` they are set as it is. Otherwise they are escaped.
 *
 * @param {string} str The string with placeholders (%s) to insert values into.
 * @param  {...any} values Primitive values to insert in place of placeholders.
 * @returns {string|Markup}
 */
export function htmlSprintf(str, ...values) {
    const valuesDict = values[0];
    if (
        valuesDict &&
        Object.prototype.toString.call(valuesDict) === "[object Object]" &&
        !(valuesDict instanceof Markup)
    ) {
        // markup: escaped base string and values (assuming sprintf itself is safe)
        return markup(
            sprintf(
                htmlEscape(str).toString(),
                Object.fromEntries(
                    Object.entries(valuesDict).map(([key, value]) => [
                        key,
                        htmlEscape(value).toString(),
                    ])
                )
            )
        );
    }
    // markup: escaped base string and values (assuming sprintf itself is safe)
    return markup(
        sprintf(
            htmlEscape(str).toString(),
            values.map((value) => htmlEscape(value).toString())
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
        // innerHTML: only Markup content is allowed
        element.innerHTML = content;
    } else {
        element.textContent = content;
    }
}
