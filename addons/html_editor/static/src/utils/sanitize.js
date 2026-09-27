import { containsAnyInline, selfClosingHtmlTags } from "./dom_info";
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
        options.wrapInlinesInBlocks(element, {
            baseContainerNodeName: "DIV",
        });
    }

    // During `convert_inline`, image elements may receive `width` and `height` attributes,
    // along with inline styles. These attributes force specific dimensions, which breaks
    // the fallback to default sizing. We remove them here to allow proper resizing behavior.
    // The attributes will be re-applied on save.
    for (const img of element.querySelectorAll("img[width], img[height]")) {
        const width = img.getAttribute("width");
        const height = img.getAttribute("height");
        img.removeAttribute("height");
        img.removeAttribute("width");
        img.style.setProperty("width", isNaN(width) ? width : `${width}px`);
        img.style.setProperty("height", isNaN(height) ? height : `${height}px`);
    }
}

/**
 * Converts XML-style self-closing tags (e.g., <div/> <span/> <t/>) into proper
 * HTML start/end tag pairs, except for true HTML void elements.
 *
 * @param {string | ReturnType<markup>} content
 * @returns {ReturnType<markup>}
 */
export function fixInvalidHTML(content) {
    if (!content) {
        return content;
    }
    // Match self-closing tags EXCEPT HTML void elements.
    // We use selfClosingHtmlTags over selfClosingElementTags because the
    // latter includes XML-only tags such as <t>, which must not be treated as
    // void in HTML.
    const voidPattern = selfClosingHtmlTags.map((t) => `${t.toLowerCase()}\\b`).join("|");
    const regex = new RegExp(
        `<\\s*(?!${voidPattern})` +
            `([a-zA-Z0-9:-]+)` + // tag name
            `\\s*` +
            `((?:(?:\\s+[\\w:-]+(?:\\s*=\\s*(?:"[^"]*"|'[^']*'|[^\\s"'=<>\\\`]+))?)*))` + // attributes
            `\\s*\\/>`,
        "g"
    );
    return htmlReplace(content, regex, (match, tag, attributes) => {
        // markup: content is either already markup or escaped in htmlReplace
        attributes = markup(attributes);
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

/**
 * Check whether the given xml string contains nodes that would be
 * silently moved when inserted as html by the browser due to qweb
 * <t> elements, but which still ouputs valid html after rendering.
 *
 * @returns {boolean} true if the value does not contain patterns
 * incompatible with direct html conversion.
 */
export function canRenderAsHTML(value) {
    if (!value) {
        return value === "";
    }
    const domParser = new DOMParser();
    const xml = domParser.parseFromString(value, "text/xml");
    const isIllegalT = (t) => {
        const ancestor = t.closest("td, th, table");
        return ancestor?.matches("table") ?? false;
    };
    return ![...xml.querySelectorAll("table t")].find(isIllegalT);
}
