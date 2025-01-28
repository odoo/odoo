import {
    StoreLocatorLocationSchedule
} from '@website/components/store_locator_map/store_locator_location_schedule';
import { Component } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';

export class StoreLocatorLocation extends Component {
    static components = { StoreLocatorLocationSchedule };
    static template = 'website.store_locator_location';
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
        hiddenLocations: {
            type: Array,
            element: String,
        },
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
