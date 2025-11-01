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
