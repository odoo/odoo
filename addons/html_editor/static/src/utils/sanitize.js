import { containsAnyInline } from "./dom_info";
import { wrapInlinesInBlocks } from "./dom";
import { markup } from "@odoo/owl";

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
 * @param {string} content
 * @returns {string}
 */
export function fixInvalidHTML(content) {
    if (!content) {
        return content;
    }
    // TODO: improve the regex to support nodes with data-attributes containing
    // `/` and `>` characters.
    const regex = /<\s*(a|strong|t|span)[^<]*?\/\s*>/g;
    return content.replace(regex, (match, g0) => match.replace(/\/\s*>/, `></${g0}>`));
}

let Markup = null;

export function instanceofMarkup(value) {
    if (!Markup) {
        Markup = markup("").constructor;
    }
    return value instanceof Markup;
}

export function applyHistorySteps(content, versionedContent) {
    const historyStepIdMatch = versionedContent.match(/data-last-history-steps\s*=\s*"([^"]+)"/);
    const versionMatch = versionedContent.match(/data-oe-version\s*=\s*"([^"]+)"/);
    const htmlContent = content.toString() || "<div></div>";
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlContent, "text/html");
    if (historyStepIdMatch?.[1]) {
        doc.body.firstChild.setAttribute("data-last-history-steps", historyStepIdMatch[1]);
    }
    if (versionMatch?.[1]) {
        doc.body.firstChild.setAttribute("data-oe-version", versionMatch[1]);
    }
    return doc.body.innerHTML;
}
