import { LocationSchedule } from "@location_selector/location_schedule/location_schedule";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class Location extends Component {
    static components = { LocationSchedule };
    static template = "location_selector.location";
    static props = {
        id: String,
        number: Number,
        name: String,
        street: String,
        city: String,
        zip: String,
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
        return `${this.props.zip} ${this.props.city}`;
    }

    get openingHoursLabel() {
        return _t("Opening hours");
    }
}
