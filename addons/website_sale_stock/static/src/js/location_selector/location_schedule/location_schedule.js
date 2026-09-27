import { Component, t, useProps } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';

export class LocationSchedule extends Component {
    static template = 'website_sale_stock.locationSelector.schedule';
    props = useProps({
        openingHours: t.record(t.array(t.string()).optional()),
        wrapClass: t.string().optional(),
    });

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
