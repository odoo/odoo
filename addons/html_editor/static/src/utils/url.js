/**
 * @param {string} url
 */
export function isImageUrl(url) {
    const urlFileExtention = url.split(".").pop();
    return ["jpg", "jpeg", "png", "gif", "svg", "webp"].includes(urlFileExtention.toLowerCase());
}
