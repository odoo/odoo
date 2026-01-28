import { htmlEscape, markup } from "@odoo/owl";
import { formatList, normalizedMatches } from "@web/core/l10n/utils";
import { unique } from "@web/core/utils/arrays";
import { escapeRegExp, mapSubstitutions, sprintf } from "@web/core/utils/strings";

/**
 * @typedef {ReturnType<markup>} Markup
 */

const Markup = markup().constructor;

/**
 * Safely creates a Document fragment from content. If content was flagged as safe HTML using
 * `markup` it is parsed as HTML. Otherwise it is escaped and parsed as text.
 *
 * @param {string | Markup} content
 */
export function createDocumentFragmentFromContent(content) {
    return new document.defaultView.DOMParser().parseFromString(htmlEscape(content), "text/html");
}

/**
 * Safely creates an element with the given content. If content was flagged as safe HTML using
 * `markup` it is set as innerHTML. Otherwise it is set as text.
 *
 * @param {string} elementName
 * @param {string | Markup} content
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
 * @param {string | Markup} query
 * @param {string | Markup} text
 * @param {string | Markup} classes
 * @returns {string | Markup}
 */
export function highlightText(query, text, classes) {
    if (!query || !text) {
        return text;
    }
    let result = text;
    const isQueryMarkup = isMarkup(query);
    const matches = unique(
        normalizedMatches(result, query).map((m) =>
            // normalizedMatch will remove Markup and return string matches
            // so it is necessary to restore the removed Markup when needed
            isQueryMarkup ? markup(m.match.toLowerCase()) : m.match.toLowerCase()
        )
    );
    for (const match of matches) {
        const regex = new RegExp(
            `(?<!&[^;]{0,5})(${escapeRegExp(htmlEscape(match))})(?=(?:[^>]*<[^<]*>)*[^<>]*$)`,
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
 * Same behavior as {@link formatList}, but producing safe HTML. If the values are
 * flagged as safe HTML using `markup()` they are set as it is. Otherwise they are
 * escaped.
 *
 * @param {Parameters<formatList>[0]} values
 * @param {Parameters<formatList>[1]} [options]
 * @returns {Markup}
 */
export function htmlFormatList(values, options) {
    // markup: args are escaped (or markup), and list separators are limited to
    // `Intl.ListFormat` strings.
    return markup(formatList(Array.from(values, htmlEscape), options));
}

/**
 * Applies list join on content and returns a markup result built for HTML.
 *
 * @param {Iterable<string | Markup>} list
 * @param {string | Markup} [separator]
 * @returns {Markup}
 */
export function htmlJoin(list, separator = "") {
    // markup: args and separator are escaped (or markup), join is considered safe
    return markup(Array.from(list, htmlEscape).join(htmlEscape(separator)));
}

/**
 * Applies string replace on content and returns a markup result built for HTML.
 *
 * @param {string | Markup} content
 * @param {string | RegExp} search
 * @param {string | (substring: string, ...args: any[]) => string | Markup} replacer
 * @returns {Markup}
 */
export function htmlReplace(content, search, replacer) {
    const isReplacerFn = typeof replacer === "function";
    if (search instanceof RegExp && !isReplacerFn) {
        throw new TypeError("htmlReplace: replacer must be a function when search is a RegExp.");
    }
    content = htmlEscape(content);
    if (typeof search === "string" || search instanceof String) {
        search = htmlEscape(search);
    }
    const safeReplacement = isReplacerFn
        ? (...args) => htmlEscape(replacer(...args))
        : htmlEscape(replacer);
    // markup: content and replacer are escaped (or markup), replace is considered safe
    return markup(content.replace(search, safeReplacement));
}

/**
 * Applies string replaceAll on content and returns a markup result built for HTML.
 *
 * @param {string | Markup} content
 * @param {string | RegExp} search
 * @param {string | (substring: string, ...args: any[]) => string | Markup} replacer
 * @returns {Markup}
 */
export function htmlReplaceAll(content, search, replacer) {
    const isReplacerFn = typeof replacer === "function";
    if (search instanceof RegExp && !isReplacerFn) {
        throw new TypeError("htmlReplaceAll: replacer must be a function when search is a RegExp.");
    }
    content = htmlEscape(content);
    if (typeof search === "string" || search instanceof String) {
        search = htmlEscape(search);
    }
    const safeReplacement = isReplacerFn
        ? (...args) => htmlEscape(replacer(...args))
        : htmlEscape(replacer);
    // markup: content and replacer are escaped (or markup), replaceAll is considered safe
    return markup(content.replaceAll(search, safeReplacement));
}

/**
 * Same behavior as sprintf, but produces safe HTML. If the string or values are flagged as safe HTML
 * using `markup()` they are set as it is. Otherwise they are escaped.
 *
 * @param {string} str The string with placeholders (%s) to insert values into.
 * @param  {...unknown[]} substitutions Primitive values to insert in place of placeholders.
 * @returns {string | Markup}
 */
export function htmlSprintf(str, ...substitutions) {
    const replaced = sprintf(htmlEscape(str), ...mapSubstitutions(substitutions, htmlEscape));
    return markup(replaced);
}

/**
 * Applies string trim on content and returns a markup result built for HTML.
 *
 * @param {string | Markup} content
 * @returns {string | Markup}
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
 * @param {string | Markup} [content]
 * @returns {boolean} true if no content found or if containing only formatting tags
 */
export function isHtmlEmpty(content = "") {
    return createElementWithContent("div", content).textContent.trim() === "";
}

/**
 * @param {unknown} content
 */
export function isMarkup(content) {
    return content instanceof Markup;
}

/**
 * Formats the given `text` as follow:
 *  - \*\*text\*\* => puts `text` in bold.
 *  - --text-- => puts `text` in "muted" (i.e. grayed out).
 *  - \`text\` => puts `text` in a rounded badge (bg-primary).
 *  - \n => inserts a line break.
 *  - \t => inserts the equivalent of 4 spaces.
 *
 * @param {string | Markup} text
 * @returns {string | Markup} the formatted text
 */
export function odoomark(text) {
    /**
     * Mapping of patterns - replacer functions to apply to odoomarked strings.
     *
     * For the content passed directly to `markup` (e.g. **bold** or ``tagged``):
     * the content is considered safe, as it directly comes from {@link htmlReplaceAll}
     * which uses {@link htmlEscape}.
     *
     * Note: this list is declared inline in the `odoomark` function to avoid other
     * functions using the marked-up replacers for injection.
     */
    const replacers = [
        // Line break
        ["\n", markup`<br>`],
        // Larger spacing
        ["\t", markup`<span style="margin-left: 2em"></span>`],
        // Bold
        [/\*\*(.+?)\*\*/g, (_, content) => markup(`<b>${content}</b>`)],
        // Muted
        [/--(.+?)--/g, (_, content) => markup(`<span class="text-muted">${content}</span>`)],
        // Badge
        [
            /&#x60;(.+?)&#x60;/g,
            (_, content) =>
                markup(
                    `<span class="o_tag position-relative d-inline-flex align-items-center mw-100 o_badge badge rounded-pill lh-1 o_tag_color_0">${content}</span>`
                ),
        ],
    ];
    for (const [pattern, replacer] of replacers) {
        text = htmlReplaceAll(text, pattern, replacer);
    }
    return text;
}

/**
 * Safely sets content on element. If content was flagged as safe HTML using `markup` it is set as
 * innerHTML. Otherwise it is set as text.
 *
 * @param {Element} element
 * @param {string | Markup} content
 */
export function setElementContent(element, content) {
    if (isMarkup(content)) {
        // innerHTML: content is markup
        element.innerHTML = content;
    } else {
        element.textContent = content;
    }
}
