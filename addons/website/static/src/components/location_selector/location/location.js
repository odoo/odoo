import { LocationSchedule } from "../location_schedule/location_schedule";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class Location extends Component {
    static components = { LocationSchedule };
    static template = "website.locationSelector.location";
    static props = {
        id: String,
        number: { type: String, optional: true },
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
            optional: true,
        },
        additionalData: { type: Object, optional: true },
        isSelected: Boolean,
        setSelectedLocation: Function,
        showPinIndicator: { type: Boolean, optional: true },
    };
    static defaultProps = {
        openingHours: {},
        showPinIndicator: true,
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
