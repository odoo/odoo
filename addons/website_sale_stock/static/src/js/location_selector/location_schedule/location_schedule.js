import { Component, t, useProps } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';

/**
 * Return the index of the current day of the week. 0 for Monday, 6 for Sunday.
 *
 * @return {Number} The index of today in the week.
 */
export function getTodayIndex() {
    return luxon.DateTime.now().weekday - 1;
}

/**
 * Return a short label describing whether the location is open today.
 *
 * @param {Object} openingHours - The opening periods, per day of the week.
 * @return {Object} The status label and whether the location is open today.
 */
export function getTodayStatus(openingHours) {
    const periods = openingHours[getTodayIndex()] || [];
    if (periods.length) {
        return { isOpen: true, label: _t("Open · %s", periods.join(", ")) };
    }
    return { isOpen: false, label: _t("Closed") };
}

export class LocationSchedule extends Component {
    static template = 'website_sale_stock.locationSelector.schedule';
    props = useProps({
        openingHours: t.record(t.array(t.string()).optional()),
        wrapClass: t.string().optional(),
    });

    todayIndex = getTodayIndex();

    /**
     * Return the localized day's name given his index in the week.
     *
     * @param {Number} weekday - The number of the day of the week. 0 for Monday, 6 for Sunday.
     * @return {Object} the localized name of the day (long version).
     */
    getWeekDay(weekday) {
        const dayName = luxon.Info.weekdays()[weekday];
        return dayName.charAt(0).toUpperCase() + dayName.slice(1);
    }

    get closedLabel() {
        return _t("Closed");
    }
}
