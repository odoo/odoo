import {
    LocationSchedule
} from '@delivery/js/location_selector/location_schedule/location_schedule';
import { Component } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';

export class Location extends Component {
    static components = { LocationSchedule };
    static template = 'delivery.locationSelector.location';
    static props = {
        id: String,
        number: Number,
        name: String,
        street: String,
        city: String,
        zipCode: String,
        openingHours: {
            type: Object,
            values: {
                type: Array,
                element: String,
                optional: true,
            },
        },
        additionalData: { type: Object, optional: true },
        isSelected: Boolean,
        setSelectedLocation: Function,
    };

    /**
     * Get the city and the zip code.
     *
     * @return {Object} The city and the zip code.
     */
    getCityAndZipCode() {
        return `${this.props.zipCode} ${this.props.city}`;
    }

    get openingHoursLabel() {
        return _t("Opening hours");
    }
}
