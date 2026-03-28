import { Component } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';

export class LocationSchedule extends Component {
    static template = 'delivery.locationSelector.schedule';
    static props = {
        openingHours: {
            type: Object,
            values: {
                type: Array,
                element: String,
                optional: true,
            },
        },
        wrapClass: { type: String, optional: true },
    };

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
