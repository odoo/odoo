const { DateTime } = luxon;

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
