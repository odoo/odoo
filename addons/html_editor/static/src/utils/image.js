import { isColorGradient } from "@web/core/utils/colors";

/**
 * Extracts url and gradient parts from the background-image CSS property.
 *
 * @param {string} CSS 'background-image' property value
 * @returns {Object} contains the separated 'url' and 'gradient' parts
 */
export function backgroundImageCssToParts(css) {
    const parts = {};
    css = css || "";
    if (css.startsWith("url(")) {
        const urlEnd = css.indexOf(")") + 1;
        parts.url = css.substring(0, urlEnd).trim();
        const commaPos = css.indexOf(",", urlEnd);
        css = commaPos > 0 ? css.substring(commaPos + 1) : "";
    }
    if (isColorGradient(css)) {
        parts.gradient = css.trim();
    }
    return parts;
}

/**
 * Combines url and gradient parts into a background-image CSS property value
 *
 * @param {Object} contains the separated 'url' and 'gradient' parts
 * @returns {string} CSS 'background-image' property value
 */
export function backgroundImagePartsToCss(parts) {
    let css = parts.url || "";
    if (parts.gradient) {
        css += (css ? ", " : "") + parts.gradient;
    }
    return css || "none";
}

/**
 * @param {HTMLImageElement} image
 * @returns {string|null} The mimetype of the image.
 */
export function getMimetype(image) {
    const src = image.getAttribute("src");

    return (
        image.dataset.computedMimetype ||
        image.dataset.mimetypeBeforeConversion ||
        (src.endsWith(".png") && "image/png") ||
        (src.endsWith(".webp") && "image/webp") ||
        (src.endsWith(".jpg") && "image/jpeg") ||
        (src.endsWith(".jpeg") && "image/jpeg") ||
        null
    );
}
