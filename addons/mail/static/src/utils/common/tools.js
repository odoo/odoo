/**
 * Converts the given base 64 url to an Uint8Array array
 * @param {string} base64Url
 * @returns {Uint8Array}
 */
export function base64UrlToUint8Array(base64Url) {
    const base64 = base64Url
        .replace(/-/g, "+")
        .replace(/_/g, "/")
        .padEnd(Math.ceil(base64Url.length / 4) * 4, "=");
    return Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
}
