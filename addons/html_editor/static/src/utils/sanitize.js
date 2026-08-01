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

    // During `convert_inline`, image elements may receive `width` and `height` attributes,
    // along with inline styles. These attributes force specific dimensions, which breaks
    // the fallback to default sizing. We remove them here to allow proper resizing behavior.
    // The attributes are re-applied on save by `convert_inline` itself.
    //
    // Opt-in, because only that pipeline puts them back. Applied to every
    // editable it also rewrites the INTRINSIC dimensions an author wrote, and
    // nothing restores those: the image is left pinned to a fixed pixel size,
    // permanently, since `img[width]` no longer matches on the next edit. Those
    // attributes are how a browser reserves the box before the image loads, and
    // an inline `width` beats the stylesheet rule that keeps the image
    // responsive.
    if (options.removeForcedImageDimensions) {
        for (const img of element.querySelectorAll("img[width], img[height]")) {
            const width = img.getAttribute("width");
            const height = img.getAttribute("height");
            img.removeAttribute("height");
            img.removeAttribute("width");
            img.style.setProperty("width", isNaN(width) ? width : `${width}px`);
            img.style.setProperty("height", isNaN(height) ? height : `${height}px`);
        }
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
