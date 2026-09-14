/** @odoo-module native */
// @ts-check

const YOUTUBE_HOSTS = new Set(["youtu.be", "youtube.com", "youtube-nocookie.com"]);
const SUPPORTED_HOSTS = new Set([
    ...YOUTUBE_HOSTS,
    "instagram.com",
    "player.vimeo.com",
    "vimeo.com",
    "dailymotion.com",
]);

/**
 * Parse absolute or protocol-relative HTTP video URLs without loading providers.
 * @param {string | undefined} src
 * @returns {URL | undefined}
 */
export function parseVideoUrl(src) {
    if (!src || !/^(?:https?:)?\/\//i.test(src)) {
        return;
    }
    try {
        return new URL(src, window.location.href);
    } catch {
        // Incomplete URLs are normal while editing a video placeholder.
    }
}

/** @param {URL | undefined} url */
export function isYoutubeUrl(url) {
    return !!url && YOUTUBE_HOSTS.has(url.hostname.replace(/^www\./, ""));
}

/** @param {URL | undefined} url */
export function isSupportedVideoUrl(url) {
    return (
        !!url &&
        !url.username &&
        !url.password &&
        SUPPORTED_HOSTS.has(url.hostname.replace(/^www\./, ""))
    );
}
