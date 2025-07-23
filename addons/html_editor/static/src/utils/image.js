import { isColorGradient } from "@web/core/utils/colors";

/**
 * Extracts url and gradient parts from the background-image CSS property.
 *
 * @param {string} CSS 'background-image' property value
 * @returns {Object} contains the separated 'url' and 'gradient' parts
 */
export function backgroundImageCssToParts(css = "") {
    const parts = {};
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
    return [parts.url, parts.gradient].filter(Boolean).join(", ") || "";
}

/**
 * @param {HTMLImageElement} image
 * @returns {string|null} The mimetype of the image.
 */
export function getMimetype(image, data = image.dataset) {
    const src = getImageSrc(image);

    return (
        data.mimetype ||
        data.mimetypeBeforeConversion ||
        (src &&
            ((src.endsWith(".png") && "image/png") ||
                (src.endsWith(".webp") && "image/webp") ||
                (src.endsWith(".jpg") && "image/jpeg") ||
                (src.endsWith(".jpeg") && "image/jpeg"))) ||
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

/**
 * Returns the src of the image, or the src of the background-image if the
 * element is not an image.
 *
 * @param {HTMLElement} el The element to get the src or background-image from.
 * @returns {string|null} The src of the image.
 */
export function getImageSrc(el) {
    if (el.tagName === "IMG") {
        return el.getAttribute("src");
    }
    // TODO: Parallax handling is incorrectly coupled with background image source.
    // The plugin transfer the `src` on a `span`, but parallax can be achieved via other means.
    // example: CSS variables without this DOM manipulation.
    // Decouple.
    if (el.querySelector(".s_parallax_bg")) {
        el = el.querySelector(".s_parallax_bg");
    }
    const url = backgroundImageCssToParts(el.style.backgroundImage).url;
    return url && getBgImageURLFromURL(url);
}

/**
 * Parse an element's background-image's url.
 *
 * @param {string} string a css value in the form 'url("...")'
 * @returns {string|false} the src of the image or false if not parsable
 */
export function getBgImageURLFromURL(url) {
    const match = url.match(/^url\((['"])(.*?)\1\)$/);
    if (!match) {
        return "";
    }
    const matchedURL = match[2];
    // Make URL relative if possible
    const fullURL = new URL(matchedURL, window.location.origin);
    if (fullURL.origin === window.location.origin) {
        return fullURL.href.slice(fullURL.origin.length);
    }
    return matchedURL;
}
