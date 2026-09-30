import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";

const ODOO_DOMAIN_REGEX = new RegExp(`^https?://${session.db}\\.odoo\\.com(/.*)?$`);

/**
 * Checks if the given URL contains the specified hostname and returns a reconstructed URL if it does.
 *
 * @param {string} url - The URL to be checked
 * @param {Array} hostname - The hostname to be included in the modified URL
 * @return {string|boolean} The modified URL with the specified hostname included, or false if the URL does not meet the conditions
 */
export function checkURL(url, hostnameList) {
    if (url) {
        let potentialURL;
        try {
            potentialURL = new URL(url);
        } catch {
            return false;
        }
        if (hostnameList.includes(potentialURL.hostname)) {
            return `https://${potentialURL.hostname}${potentialURL.pathname}`;
        }
    }
    return false;
}

/**
 * @param {string} url
 */
export function isImageUrl(url) {
    const urlFileExtention = url.split(".").pop();
    return ["jpg", "jpeg", "png", "gif", "svg", "webp"].includes(urlFileExtention.toLowerCase());
}

/**
 * @param {string} platform
 * @param {string} videoId
 * @param {Object} params
 * @throws {Error} if the given video config is not recognized
 * @returns {URL}
 */
export function getVideoUrl(platform, videoId, params) {
    let url;
    switch (platform) {
        case "youtube":
            url = new URL(`https://www.youtube.com/embed/${videoId}`);
            break;
        case "vimeo":
            url = new URL(`https://player.vimeo.com/video/${videoId}`);
            break;
        case "dailymotion":
            url = new URL(`https://www.dailymotion.com/embed/video/${videoId}`);
            break;
        case "instagram":
            url = new URL(`https://www.instagram.com/p/${videoId}/embed`);
            break;
        default:
            throw new Error(`Unsupported platform: ${platform}`);
    }
    url.search = new URLSearchParams(params);
    return url;
}

/**
 * Checks if the given URL is using the domain where the content being
 * edited is reachable, i.e. if this URL should be stripped of its domain
 * part and converted to a relative URL if put as a link in the content.
 *
 * @param {string} url
 * @returns {boolean}
 */
export function isAbsoluteURLInCurrentDomain(url, env = null) {
    // First check if it is a relative URL: if it is, we don't want to check
    // further as we will always leave those untouched.
    let hasProtocol;
    try {
        hasProtocol = !!new URL(url).protocol;
    } catch {
        hasProtocol = false;
    }
    if (!hasProtocol) {
        return false;
    }

    const urlObj = new URL(url, window.location.origin);
    return (
        urlObj.origin === window.location.origin ||
        // Chosen heuristic to detect someone trying to enter a link using
        // its Odoo instance domain. We just suppose it should be a relative
        // URL (if unexpected behavior, the user can just not enter its Odoo
        // instance domain but its real domain, or opt-out from the domain
        // stripping). Mentioning an .odoo.com domain, especially its own
        // one, is always a bad practice anyway.
        ODOO_DOMAIN_REGEX.test(urlObj.origin)
    );
}

export function scrollAndHighlightHeading(
    content,
    headingId = browser?.location?.hash?.replace?.(/^#/, "")
) {
    if (content && headingId) {
        // Wait until the browser has rendered the editor before
        // scrolling. The timeout value of 500 is a little arbitrary,
        // but it should be enough to prevent an irritating case where
        // a Youtube video is in the document and loads while the
        // autoscroll is happening, and stops it.
        setTimeout(() => {
            const heading = content.querySelector(`[data-heading-link-id="${headingId}"]`);
            if (heading) {
                heading.scrollIntoView({ behavior: "smooth" });
                heading.classList.add("o-highlight-heading");
                setTimeout(() => {
                    heading.classList.remove("o-highlight-heading");
                }, 2000);
            }
        }, 500);
    }
}
