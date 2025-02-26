import { markup } from "@odoo/owl";

import { formatList } from "@web/core/l10n/utils";
import { patch } from "@web/core/utils/patch";
import { sprintf } from "@web/core/utils/strings";

export const Markup = markup().constructor;

/** @type {Markup} */
const markupStaticPatch = {
    /**
     * Safely creates a string with the given template and params. If a param was flagged as safe HTML
     * using `markup()` it is set as it is. Otherwise it is escaped.
     *
     * @param {string[]} strings
     * @param {Array<string|ReturnType<markup>>} values
     * @returns {ReturnType<markup>}
     */
    build(strings, ...values) {
        return strings.reduce((res, str, i) => Markup.join([res, markup(str), values[i]]), "");
    },
    /**
     * Safely creates an element with the given content. If content was flagged as safe HTML using
     * `markup()` it is set as innerHTML. Otherwise it is set as text.
     *
     * @param {string} elementName
     * @param {string|ReturnType<markup>} content
     * @returns {Element}
     */
    createElementWithContent(elementName, content) {
        const element = document.createElement(elementName);
        Markup.setElementContent(element, content);
        return element;
    },
    /**
     * Escapes content for HTML. Content is unchanged if it is already a Markup.
     *
     * @param {string|ReturnType<markup>} content
     * @returns {ReturnType<markup>}
     */
    escape(content) {
        return content instanceof Markup ? content : markup(escape(content));
    },
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
    formatList(list, ...args) {
        return markup(
            formatList(
                Array.from(list, (val) => Markup.escape(val).toString()),
                ...args
            )
        );
    },
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
    isEmpty(content = "") {
        return Markup.createElementWithContent("div", content).textContent.trim() === "";
    },
    /**
     * Applies list join on content and returns a markup result built for HTML.
     *
     * @param {Array<string|ReturnType<markup>>} args
     * @returns {ReturnType<markup>}
     */
    join(list, separator = "") {
        return markup(list.map((arg) => Markup.escape(arg)).join(Markup.escape(separator)));
    },
    /**
     * Safely sets content on element. If content was flagged as safe HTML using `markup()` it is set as
     * innerHTML. Otherwise it is set as text.
     *
     * @param {Element} element
     * @param {string|ReturnType<markup>} content
     */
    setElementContent(element, content) {
        if (content instanceof Markup) {
            element.innerHTML = content;
        } else {
            element.textContent = content;
        }
    },
    /**
     * Same behavior as sprintf, but produces safe HTML. If the string or values are flagged as safe HTML
     * using `markup()` they are set as it is. Otherwise they are escaped.
     *
     * @param {string} str The string with placeholders (%s) to insert values into.
     * @param  {...any} values Primitive values to insert in place of placeholders.
     * @returns {string|Markup}
     */
    sprintf(str, ...values) {
        const valuesDict = values[0];
        if (
            valuesDict &&
            Object.prototype.toString.call(valuesDict) === "[object Object]" &&
            !(valuesDict instanceof Markup)
        ) {
            return markup(
                sprintf(
                    Markup.escape(str).toString(),
                    Object.fromEntries(
                        Object.entries(valuesDict).map(([key, value]) => [
                            key,
                            Markup.escape(value).toString(),
                        ])
                    )
                )
            );
        }
        return markup(
            sprintf(
                Markup.escape(str).toString(),
                values.map((value) => Markup.escape(value).toString())
            )
        );
    },
};
patch(Markup, markupStaticPatch);

/**
 * Escapes a string for HTML.
 *
 * @param {string | number} [str] the string to escape
 * @returns {string} an escaped string
 */
function escape(str) {
    if (str === undefined) {
        return "";
    }
    if (typeof str === "number") {
        return String(str);
    }
    [
        ["&", "&amp;"],
        ["<", "&lt;"],
        [">", "&gt;"],
        ["'", "&#x27;"],
        ['"', "&quot;"],
        ["`", "&#x60;"],
    ].forEach((pairs) => {
        str = String(str).replaceAll(pairs[0], pairs[1]);
    });
    return str;
}
