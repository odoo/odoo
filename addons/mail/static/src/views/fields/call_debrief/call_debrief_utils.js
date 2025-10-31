/** @odoo-module **/

/**
 * Formats a duration in seconds into a MM:SS string.
 * @param {number} seconds
 * @returns {string}
 **/
export function formatDuration(seconds) {
    if (isNaN(seconds)) {
        return "00:00";
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`;
}
