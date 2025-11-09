import { htmlEscape, markup } from "@odoo/owl";

import { formatList, normalizedMatches } from "@web/core/l10n/utils";
import { unique } from "@web/core/utils/arrays";
import { escapeRegExp, sprintf } from "@web/core/utils/strings";

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
 * Returns a markuped version of the input text where
 * the query is highlighted using the input classes
 * if it is part of the text. Will normalize the query
 * for advanced symbols matching
 *
 * @param {string | ReturnType<markup>} query
 * @param {string | ReturnType<markup>} text
 * @param {string | ReturnType<markup>} classes
 * @returns {string | ReturnType<markup>}
 */
export function highlightText(query, text, classes) {
    if (!query) {
        return text;
    }
    const matches = unique(
        normalizedMatches(text, query).map((m) =>
            // normalizedMatch will remove Markup and return string matches
            // so it is necessary to restore the removed Markup when needed
            query instanceof Markup ? markup(m.match.toLowerCase()) : m.match.toLowerCase()
        )
    );
    let result = text;
    for (const match of matches) {
        const regex = new RegExp(
            `(${escapeRegExp(htmlEscape(match))})(?=(?:[^>]*<[^<]*>)*[^<>]*$)`,
            "ig"
        );
        result = htmlReplace(result, regex, (_, match) => {
            /**
             * markup: text is a Markup object (either escaped inside htmlReplace or
             * flagged safe), `match` is directly coming from this value,
             * and the regex doesn't do anything crazy to unescape it.
             */
            match = markup(match);
            return markup`<span class="${classes}">${match}</span>`;
        });
    }
    return result;
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
 * Format the text as follow:
 *      \*\*text\*\* => Put the text in bold.
 *      --text-- => Put the text in muted.
 *      \`text\` => Put the text in a rounded badge (bg-primary).
 *      \n => Insert a breakline.
 *      \t => Insert 4 spaces.
 *
 * @param {string|ReturnType<markup>} text
 * @returns {string|ReturnType<markup>} the formatted text
 */
export function odoomark(text) {
    const replacements = [
        [/\n/g, () => markup`<br/>`],
        [/\t/g, () => markup`<span style="margin-left: 2em"></span>`],
        [
            /\*\*(.+?)\*\*/g,
            (_, bold) => {
                /**
                 * markup: text is a Markup object (either escaped inside htmlReplace or
                 * flagged safe), `bold` is directly coming from this value,
                 * and the regex doesn't do anything crazy to unescape it.
                 */
                markup(bold);
                return markup`<b>${bold}</b>`;
            },
        ],
        [
            /--(.+?)--/g,
            (_, muted) => {
                /**
                 * markup: text is a Markup object (either escaped inside htmlReplace or
                 * flagged safe), `muted` is directly coming from this value,
                 * and the regex doesn't do anything crazy to unescape it.
                 */
                muted = markup(muted);
                return markup`<span class='text-muted'>${muted}</span>`;
            },
        ],
        [
            /&#x60;(.+?)&#x60;/g,
            (_, tag) => {
                /**
                 * markup: text is a Markup object (either escaped inside htmlReplace or
                 * flagged safe), `tag` is directly coming from this value,
                 * and the regex doesn't do anything crazy to unescape it.
                 */
                tag = markup(tag);
                return markup`<span class="o_tag position-relative d-inline-flex align-items-center mw-100 o_badge badge rounded-pill lh-1 o_tag_color_0">${tag}</span>`;
            },
        ],
    ];
    for (const replacement of replacements) {
        text = htmlReplaceAll(text, replacement[0], replacement[1]);
    }
    return text;
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

export function isMarkup(content) {
    return content instanceof Markup;
}
