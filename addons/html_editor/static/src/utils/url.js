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
 * @param {object} params
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
        case "youku":
            url = new URL(`https://player.youku.com/embed/${videoId}`);
            break;
        default:
            throw new Error(`Unsupported platform: ${platform}`);
    }
    url.search = new URLSearchParams(params);
    return url;
}
