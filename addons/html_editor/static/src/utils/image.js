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

/**
 * @param {HTMLImageElement} img
 * @returns {Promise<Boolean>}
 */
export async function isImageCorsProtected(img) {
    const src = img.getAttribute("src");
    if (!src) {
        return false;
    }
    let isCorsProtected = false;
    if (!src.startsWith("/") || /\/web\/image\/\d+-redirect\//.test(src)) {
        // The `fetch()` used later in the code might fail if the image is
        // CORS protected. We check upfront if it's the case.
        // Two possible cases:
        // 1. the `src` is an absolute URL from another domain.
        //    For instance, abc.odoo.com vs abc.com which are actually the
        //    same database behind.
        // 2. A "attachment-url" which is just a redirect to the real image
        //    which could be hosted on another website.
        isCorsProtected = await fetch(src, { method: "HEAD" })
            .then(() => false)
            .catch(() => true);
    }
    return isCorsProtected;
}

/**
 * @param {string} src
 * @returns {Promise<Boolean>}
 */
export async function isSrcCorsProtected(src) {
    const dummyImg = document.createElement("img");
    dummyImg.src = src;
    return isImageCorsProtected(dummyImg);
}
