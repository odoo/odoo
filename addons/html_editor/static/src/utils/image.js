import { isColorGradient } from "./color";
import { registry } from "@web/core/registry";

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
 * Converts a camel case string to snake case.
 *
 * @param {string} camelString - the camel case string to convert to snake case.
 * @returns {string} The snake case version of camelString.
 */
export function convertCamelToSnakeString(camelString) {
    return camelString.replace(/([a-z])([A-Z])/g, "$1_$2").toLowerCase();
}

/**
 * Parse an element's background-image's url.
 *
 * @param {string} string a css value in the form 'url("...")'
 * @returns {string|false} the src of the image or false if not parsable
 */
export function getBgImageURL(el) {
    const parts = backgroundImageCssToParts($(el).css('background-image'));
    const string = parts.url || '';
    const match = string.match(/^url\((['"])(.*?)\1\)$/);
    if (!match) {
        return '';
    }
    const matchedURL = match[2];
    // Make URL relative if possible
    const fullURL = new URL(matchedURL, window.location.origin);
    if (fullURL.origin === window.location.origin) {
        return fullURL.href.slice(fullURL.origin.length);
    }
    return matchedURL;
}

/**
 * Returns the data associated to imgEl.
 *
 * @param {HTMLImageElement} imgEl
 * @returns {Object} A proxy of the data associated to imgEl.
 */
export function getImageData(imgEl) {
    const imgSrc = imgEl.getAttribute("src");
    const imageData = registry.category("image.data").get(imgSrc, {});
    return Object.assign({}, imageData);
}

/**
 * Updates the "image.data" registry thanks to imgSrc (key) and a copy of
 * imageData (value).
 *
 * @param {string} imgSrc - the source of the image whose data must be updated
 * on the "image.data" registry.
 * @param {Object} imageData - the data whose copy must be updated on the
 * registry.
 */
export function updateImageDataRegistry(imgSrc, imageData) {
    const imageDataCopy = Object.assign({}, imageData);
    registry.category("image.data").add(imgSrc, imageDataCopy, { force: true });
}
