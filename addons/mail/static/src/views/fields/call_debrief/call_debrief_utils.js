import { formatFloatTime } from "@web/views/fields/formatters";

/**
 * Formats a duration in seconds as a timestamp.
 * Omits the hours portion when totalDuration is under an hour.
 * @param {number} seconds
 * @param {number} totalDuration
 * @returns {string}
 */
export function formatDuration(seconds, totalDuration) {
    const formatted = formatFloatTime(seconds || 0, {
        unit: "seconds",
        showSeconds: true,
        numeric: true,
    });
    if (totalDuration < 3600) {
        return formatted.slice(2);
    }
    return formatted;
}
