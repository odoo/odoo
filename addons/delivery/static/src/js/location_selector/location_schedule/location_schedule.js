/** @odoo-module **/

import { Component } from '@odoo/owl';

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
        return luxon.Info.weekdays()[weekday]
    }
}
