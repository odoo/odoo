const { DateTime } = luxon;
import { formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";

/**
 * @param {luxon.DateTime} datetime
 */
export function computeDelay(datetime) {
    if (!datetime) {
        return 0;
    }
    const today = DateTime.now().startOf("day");
    return datetime.diff(today, "days").days;
}

export function getMsToTomorrow() {
    const now = new Date();
    const night = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate() + 1, // the next day
        0,
        0,
        0 // at 00:00:00 hours
    );
    return night.getTime() - now.getTime();
}

export function isToday(datetime) {
    if (!datetime) {
        return false;
    }
    return (
        datetime.toLocaleString(DateTime.DATE_FULL) ===
        DateTime.now().toLocaleString(DateTime.DATE_FULL)
    );
}

/**
 * Starts a real-time updater that computes and sends the other user's local time and date to a callback every minute.
 *
 * @param {string} currentUserTimezone - The timezone of the current user.
 * @param {string} otherUserTimezone - The timezone of the user being displayed.
 * @param {Function} updateCallback - Callback receiving an object with `otherUserTime` and `otherUserDate`.
 * @returns {Function} cleanup - Call this to stop the updates.
 */
export function showRealtimeTzDiff(currentUserTimezone, otherUserTimezone, updateCallback) {
    let intervalId = null;
    let timeoutId = null;
    const updateDisplayedTime = () => {
        const now = DateTime.now();
        const currentUserDateTime = now.setZone(currentUserTimezone);
        const otherUserDateTime = now.setZone(otherUserTimezone);
        const otherUserTime = formatDateTime(otherUserDateTime, { tz: otherUserTimezone, format: "hh:mm a" });
        const otherUserDate = currentUserDateTime.hasSame(otherUserDateTime, 'day') ? null : formatDateTime(otherUserDateTime, { tz: otherUserTimezone, format: localization.dateFormat });
        updateCallback({
            otherUserTime: otherUserTime,
            otherUserDate: otherUserDate
        });
    };
    updateDisplayedTime();
    const msUntilNextMinute = 60000 - (Date.now() % 60000);
    timeoutId = setTimeout(() => {
        updateDisplayedTime();
        intervalId = setInterval(updateDisplayedTime, 60000);
    }, msUntilNextMinute);
    return () => {
        if (timeoutId) clearTimeout(timeoutId);
        if (intervalId) clearInterval(intervalId);
    };
}
