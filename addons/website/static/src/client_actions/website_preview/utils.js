/**
 * Checks if the 2 given URLs are the same, to prevent redirecting uselessly
 * from one to another.
 * It will consider naked URL and `www` URL as the same URL.
 * It will consider `https` URL `http` URL as the same URL.
 *
 * @param {string} url1
 * @param {string} url2
 * @returns {Boolean}
 */
export function isHTTPSorNakedDomainRedirection(url1, url2) {
    try {
        url1 = new URL(url1).host;
        url2 = new URL(url2).host;
    } catch {
        // Incorrect URL, `false` URL..
        return false;
    }
    return url1 === url2 || url1.replace(/^www\./, "") === url2.replace(/^www\./, "");
}
