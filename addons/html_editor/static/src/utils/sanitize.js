import { containsAnyInline } from "./dom_info";
import { wrapInlinesInBlocks } from "./dom";
import { markup } from "@odoo/owl";
import { htmlReplace } from "@web/core/utils/html";

export function initElementForEdition(element, options = {}) {
    if (
        element?.nodeType === Node.ELEMENT_NODE &&
        containsAnyInline(element) &&
        !options.allowInlineAtRoot
    ) {
        // No matter the inline content, it will be wrapped in a DIV to try
        // and match the current style of the content as much as possible.
        // (P has a margin-bottom, DIV does not).
        wrapInlinesInBlocks(element, {
            baseContainerNodeName: "DIV",
        });
    }
}

/**
 * Properly close common XML-like self-closing elements to avoid HTML parsing
 * issues.
 *
 * @param {string | ReturnType<markup>} content should be a valid XML/HTML string or a markup object.
 * @returns {ReturnType<markup>}
 */
export function fixInvalidHTML(content) {
    if (!content) {
        return content;
    }
    if (!instanceofMarkup(content)) {
        // markup: content should be a valid XML/HTML string
        // should be wrapped in markup otherwise it will be escaped in htmlReplace
        content = markup(content);
    }
    // TODO: improve the regex to support nodes with data-attributes containing
    // `/` and `>` characters.
    const regex = /<\s*(a|strong|t|span)([^<]*?)\/\s*>/g;
    return htmlReplace(content, regex, (match, tag, attributes) => {
        // markup: content is either already markup or escaped in htmlReplace
        attributes = markup(attributes);
        // markup: tag can only take one of the pre-defined values in the regex
        tag = markup(tag);
        return markup`<${tag}${attributes}></${tag}>`;
    });
}

let Markup = null;

export function instanceofMarkup(value) {
    if (!Markup) {
        Markup = markup("").constructor;
    }
    return value instanceof Markup;
}
